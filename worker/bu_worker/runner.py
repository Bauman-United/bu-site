import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from bu_core.models import IngestRun, News
from bu_core.recompute import recompute
from bu_core.settings import Settings
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.pipeline import content as content_pipeline
from bu_worker.pipeline import joinfootball as jf_pipeline
from bu_worker.pipeline import telegram as telegram_pipeline
from bu_worker.pipeline.common import IngestResult
from bu_worker.sources.content import load_content
from bu_worker.sources.ingame.fetch import fetch_bundles as fetch_ingame_bundles
from bu_worker.sources.joinfootball.discover import discover_tournament_seasons
from bu_worker.sources.joinfootball.fetch import fetch_bundle
from bu_worker.sources.lfl.fetch import fetch_bundle as fetch_lfl_bundle
from bu_worker.sources.lfl.parse import parse_club_tournament_ids
from bu_worker.sources.telegram import fetch_posts as fetch_tg_posts

log = logging.getLogger(__name__)
MSK = ZoneInfo("Europe/Moscow")


def revalidate(
    settings: Settings, tags: set[str], transport: httpx.BaseTransport | None = None
) -> None:
    if not settings.revalidate_url or not tags:
        return
    try:
        with httpx.Client(transport=transport, timeout=10) as client:
            client.post(
                settings.revalidate_url,
                json={"tags": sorted(tags)},
                headers={"Authorization": f"Bearer {settings.revalidate_secret or ''}"},
            )
    except httpx.HTTPError:
        log.exception("revalidate failed")


def _record(
    session: Session, source: str, started: datetime, status: str, counts: dict, error: str | None
) -> None:
    session.add(
        IngestRun(
            source=source,
            started_at=started,
            finished_at=datetime.now(UTC),
            status=status,
            counts=counts,
            error=error,
        )
    )
    session.commit()


@dataclass(frozen=True)
class SourceSpec:
    """Источник турниров: лига на joinsport (БЛ — «joinfootball», IFL, Urban Cup…) или lfl."""

    name: str
    base: str
    team_id: str  # наша команда: team_id на joinsport, club_id в ЛФЛ
    current_ids: list[str]


def history_sources(settings: Settings) -> tuple[str, ...]:
    """Все источники для `run history`: лиги joinsport из настроек и ЛФЛ."""
    return (*(j.key for j in settings.joinsport_sources), "lfl")


def source_spec(settings: Settings, name: str) -> SourceSpec:
    if name == "lfl":
        s = settings
        return SourceSpec(name, s.lfl_base, s.lfl_club_id, s.lfl_tournament_ids)
    for j in settings.joinsport_sources:
        if j.key == name:
            return SourceSpec(name, j.base, j.team_id, j.tournament_ids)
    raise ValueError(name)


def make_client(settings: Settings, name: str) -> PoliteClient:
    return PoliteClient(
        source_spec(settings, name).base,
        f"BaumanUnitedBot/1.0 (+{settings.site_url})",
        settings.request_delay_s,
    )


def make_ingame_client(settings: Settings) -> PoliteClient:
    return PoliteClient(
        settings.ingame_base,
        f"BaumanUnitedBot/1.0 (+{settings.site_url})",
        settings.request_delay_s,
    )


def _today() -> date:
    return datetime.now(MSK).date()


def _ingest_tournament(
    session: Session,
    settings: Settings,
    client: PoliteClient,
    spec: SourceSpec,
    tid: str,
    started: datetime,
    today: date,
    season_id: str | None = None,
) -> IngestResult:
    root = Path(settings.snapshot_dir)

    def snap(name: str, html: str) -> None:
        snapshots.save(root, f"{spec.name}/{tid}", name, html, started)

    match_url: Callable[[str], str] | None = None
    if spec.name == "lfl":
        bundle = fetch_lfl_bundle(client, tid, spec.team_id, spec.base, snap)
        match_url = lambda match_id: f"{spec.base}/match{match_id}"  # noqa: E731
    else:
        team_calendar = (
            f"/team/{spec.team_id}/calendar?season_id={season_id}" if season_id else None
        )
        bundle = fetch_bundle(client, tid, spec.team_id, spec.base, snap, today, team_calendar)
    jf_pipeline.sanity_check(
        session,
        f"{spec.name}:{tid}",
        bundle,
        require_standings="кубок" not in bundle.tournament.name.lower() and not bundle.multi_stage,
    )
    return jf_pipeline.ingest(
        session,
        bundle,
        spec.team_id,
        settings.our_team_names,
        source=spec.name,
        match_url=match_url,
        today=today,
    )


def _run_tournaments(
    session: Session,
    settings: Settings,
    client: PoliteClient,
    notifier: Notifier,
    spec: SourceSpec,
    tids: list[str],
    *,
    today: date,
    refresh: bool,
    limit: int | None = None,
    seasons: Mapping[str, str] | None = None,
) -> tuple[str, set[str]]:
    """Качает турниры по одному; закончившиеся и уже загруженные (архив) пропускает."""
    overall = "ok"
    all_tags: set[str] = set()
    done = 0
    for tid in tids:
        if limit is not None and done >= limit:
            break
        if not refresh and jf_pipeline.is_archived(session, spec.name, tid, today):
            log.debug("%s:%s archived, skipped", spec.name, tid)
            continue
        done += 1
        source = f"{spec.name}:{tid}"
        started = datetime.now(UTC)
        try:
            result = _ingest_tournament(
                session, settings, client, spec, tid, started, today, (seasons or {}).get(tid)
            )
            recompute(session)
            session.commit()
        except jf_pipeline.SanityError as exc:
            session.rollback()
            _record(session, source, started, "rejected", {}, str(exc))
            notifier.send(f"{source}: данные отклонены — {exc}", key=f"{source}:rejected")
            overall = "rejected"
            continue
        except Exception as exc:  # noqa: BLE001 — любая ошибка источника не должна ронять воркер
            session.rollback()
            log.exception("%s failed", source)
            _record(session, source, started, "error", {}, repr(exc))
            notifier.send(f"{source}: ошибка — {exc!r}", key=f"{source}:error")
            overall = "error"
            continue
        _record(session, source, started, "ok", result.counts, None)
        for warning in result.warnings:
            notifier.send(warning, key=f"warn:{warning}")
        all_tags |= result.tags
    return overall, all_tags


def _run_current(
    name: str,
    session: Session,
    settings: Settings,
    client: PoliteClient,
    notifier: Notifier,
    today: date | None,
    refresh: bool | None,
) -> str:
    spec = source_spec(settings, name)
    status, tags = _run_tournaments(
        session,
        settings,
        client,
        notifier,
        spec,
        spec.current_ids,
        today=today or _today(),
        refresh=settings.history_refresh if refresh is None else refresh,
    )
    revalidate(settings, tags)
    return status


def run_joinfootball(
    session: Session,
    settings: Settings,
    client: PoliteClient,
    notifier: Notifier,
    *,
    today: date | None = None,
    refresh: bool | None = None,
) -> str:
    return _run_current("joinfootball", session, settings, client, notifier, today, refresh)


def run_lfl(
    session: Session,
    settings: Settings,
    client: PoliteClient,
    notifier: Notifier,
    *,
    today: date | None = None,
    refresh: bool | None = None,
) -> str:
    return _run_current("lfl", session, settings, client, notifier, today, refresh)


def run_ingame(
    session: Session,
    settings: Settings,
    client: PoliteClient,
    notifier: Notifier,
    *,
    today: date | None = None,
    refresh: bool | None = None,
) -> str:
    """Импортирует исторические сезоны команды из JSON API InGame Sports."""
    force = settings.history_refresh if refresh is None else refresh
    run_day = today or _today()
    known = set()
    if not force:
        sources = session.scalars(
            select(IngestRun.source).where(
                IngestRun.source.like("ingame:%"), IngestRun.status == "ok"
            )
        )
        known = {
            season_id
            for source in sources
            if jf_pipeline.is_archived(
                session, "ingame", season_id := source.split(":", 1)[1], run_day
            )
        }

    started = datetime.now(UTC)
    root = Path(settings.snapshot_dir)

    def snap(name: str, body: str) -> None:
        snapshots.save(root, "ingame", name, body, started, suffix="json")

    try:
        bundles = fetch_ingame_bundles(
            client,
            settings.ingame_team_id,
            settings.ingame_public_base,
            settings.ingame_base,
            snap,
            skip_seasons=known,
        )
    except Exception as exc:  # noqa: BLE001 — сбой источника не должен ронять воркер
        session.rollback()
        log.exception("ingame fetch failed")
        _record(session, "ingame:overview", started, "error", {}, repr(exc))
        notifier.send(f"ingame: ошибка — {exc!r}", key="ingame:error")
        return "error"

    overall = "ok"
    tags: set[str] = set()
    for bundle in bundles:
        season_id = bundle.tournament.external_id
        source = f"ingame:{season_id}"
        season_started = datetime.now(UTC)
        try:
            jf_pipeline.sanity_check(session, source, bundle, require_standings=False)
            result = jf_pipeline.ingest(
                session,
                bundle,
                settings.ingame_team_id,
                settings.our_team_names,
                source="ingame",
                match_url=lambda match_id: (
                    f"{settings.ingame_public_base}/amf_5x5/match/{match_id}"
                ),
                today=run_day,
            )
            recompute(session)
            session.commit()
        except Exception as exc:  # noqa: BLE001 — следующий сезон всё равно импортируем
            session.rollback()
            log.exception("%s failed", source)
            _record(session, source, season_started, "error", {}, repr(exc))
            notifier.send(f"{source}: ошибка — {exc!r}", key=f"{source}:error")
            overall = "error"
            continue
        _record(session, source, season_started, "ok", result.counts, None)
        tags |= result.tags
    revalidate(settings, tags)
    return overall


def discover(spec: SourceSpec, client: PoliteClient) -> dict[str, str | None]:
    """Все турниры нашей команды в источнике, от старых к новым → сезон на joinsport."""
    if spec.name == "lfl":
        ids = reversed(parse_club_tournament_ids(client.get(f"/club{spec.team_id}")))
        return dict.fromkeys(ids)
    return dict(discover_tournament_seasons(client, spec.team_id))


def run_history(
    session: Session,
    settings: Settings,
    clients: Mapping[str, PoliteClient],
    notifier: Notifier,
    *,
    sources: Sequence[str] | None = None,
    limit: int | None = None,
    today: date | None = None,
    refresh: bool | None = None,
) -> str:
    """Прошлые сезоны: находит все турниры команды и качает неархивные.

    Текущие турниры из настроек пропускаются — их ведёт обычный запуск раз в 6 часов.
    `limit` — не больше N турниров на источник (проверка на живом сайте).
    """
    overall = "ok"
    all_tags: set[str] = set()
    for name in sources if sources is not None else history_sources(settings):
        spec = source_spec(settings, name)
        client = clients[name]
        try:
            found = discover(spec, client)
        except Exception as exc:  # noqa: BLE001 — сбой одного источника не роняет остальные
            log.exception("%s discovery failed", name)
            notifier.send(f"{name}: поиск турниров — ошибка {exc!r}", key=f"{name}:discover")
            overall = "error"
            continue
        tids = [t for t in found if t not in spec.current_ids]
        log.info("%s: %s tournaments found, %s past", name, len(found), len(tids))
        status, tags = _run_tournaments(
            session,
            settings,
            client,
            notifier,
            spec,
            tids,
            today=today or _today(),
            refresh=settings.history_refresh if refresh is None else refresh,
            limit=limit,
            seasons={t: season for t, season in found.items() if season},
        )
        if status != "ok":
            overall = status
        all_tags |= tags
    revalidate(settings, all_tags)
    return overall


def run_telegram(
    session: Session,
    settings: Settings,
    client: PoliteClient,
    notifier: Notifier,
    *,
    full_rescan: bool | None = None,
) -> str:
    source = f"telegram:{settings.tg_channel}"
    started = datetime.now(UTC)
    root = Path(settings.snapshot_dir)
    try:
        known = session.scalars(select(News.slug).where(News.origin == "telegram")).all()
        known_ids = [int(slug.removeprefix("tg-")) for slug in known]
        posts = fetch_tg_posts(
            client,
            settings.tg_channel,
            since=settings.tg_since,
            known_max_id=(
                None if settings.tg_full_rescan or full_rescan else max(known_ids, default=None)
            ),
            max_pages=settings.tg_max_pages,
            snapshot=lambda name, html: snapshots.save(root, "telegram", name, html, started),
        )
        result = telegram_pipeline.ingest(session, posts)
        session.commit()
    except Exception as exc:  # noqa: BLE001 — сбой канала не должен ронять остальные источники
        session.rollback()
        log.exception("telegram failed")
        _record(session, source, started, "error", {}, repr(exc))
        notifier.send(f"{source}: ошибка — {exc!r}", key=f"{source}:error")
        return "error"
    _record(session, source, started, "ok", result.counts, None)
    revalidate(settings, result.tags)
    return "ok"


def run_content(session: Session, settings: Settings) -> str:
    started = datetime.now(UTC)
    bundle = load_content(Path(settings.content_dir))  # ContentError пробрасывается — деплой падает
    result = content_pipeline.sync_content(session, bundle)
    recompute(session)
    session.commit()
    _record(session, "content", started, "ok", result.counts, None)
    for warning in result.warnings:
        log.warning(warning)
    revalidate(settings, result.tags)
    return "ok"


def run_migrate_seasons(sessions: Callable[[], Session], settings: Settings) -> int:
    """`python -m bu_worker migrate-seasons`: разовый перевод сезонов на календарные годы."""
    from bu_worker.pipeline.seasons import migrate_seasons

    with sessions() as session:
        report = migrate_seasons(session)
        session.commit()
    log.info("migrate-seasons: %s", report)
    revalidate(settings, {"home", "matches", "players", "standings"})
    return 0
