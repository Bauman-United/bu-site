import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bu_core.models import IngestRun
from bu_core.recompute import recompute
from bu_core.settings import Settings
from sqlalchemy.orm import Session

from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.pipeline import content as content_pipeline
from bu_worker.pipeline import joinfootball as jf_pipeline
from bu_worker.pipeline import lfl as lfl_pipeline
from bu_worker.sources.content import load_content
from bu_worker.sources.joinfootball.fetch import fetch_bundle
from bu_worker.sources.lfl.fetch import fetch_bundle as fetch_lfl_bundle

log = logging.getLogger(__name__)


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


def run_joinfootball(
    session: Session, settings: Settings, client: PoliteClient, notifier: Notifier
) -> str:
    overall = "ok"
    all_tags: set[str] = set()
    root = Path(settings.snapshot_dir)
    for tid in settings.joinfootball_tournament_ids:
        source = f"joinfootball:{tid}"
        started = datetime.now(UTC)

        def snap(name: str, html: str, _tid: str = tid, _started: datetime = started) -> None:
            snapshots.save(root, f"joinfootball/{_tid}", name, html, _started)

        try:
            bundle = fetch_bundle(
                client, tid, settings.joinfootball_team_id, settings.joinfootball_base, snap
            )
            jf_pipeline.sanity_check(session, source, bundle)
            result = jf_pipeline.ingest(
                session, bundle, settings.joinfootball_team_id, settings.our_team_names
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
            log.exception("joinfootball %s failed", tid)
            _record(session, source, started, "error", {}, repr(exc))
            notifier.send(f"{source}: ошибка — {exc!r}", key=f"{source}:error")
            overall = "error"
            continue
        _record(session, source, started, "ok", result.counts, None)
        for warning in result.warnings:
            notifier.send(warning, key=f"warn:{warning}")
        all_tags |= result.tags
    revalidate(settings, all_tags)
    return overall


def run_lfl(session: Session, settings: Settings, client: PoliteClient, notifier: Notifier) -> str:
    overall = "ok"
    all_tags: set[str] = set()
    root = Path(settings.snapshot_dir)
    for tid in settings.lfl_tournament_ids:
        source = f"lfl:{tid}"
        started = datetime.now(UTC)

        def snap(name: str, html: str, _tid: str = tid, _started: datetime = started) -> None:
            snapshots.save(root, f"lfl/{_tid}", name, html, _started)

        try:
            bundle = fetch_lfl_bundle(client, tid, settings.lfl_club_id, settings.lfl_base, snap)
            lfl_pipeline.sanity_check(
                session,
                source,
                bundle,
                require_standings="кубок" not in bundle.tournament.name.lower(),
            )
            result = lfl_pipeline.ingest(
                session,
                bundle,
                settings.lfl_club_id,
                settings.our_team_names,
                lambda match_id: f"{settings.lfl_base}/match{match_id}",
            )
            recompute(session)
            session.commit()
        except lfl_pipeline.SanityError as exc:
            session.rollback()
            _record(session, source, started, "rejected", {}, str(exc))
            notifier.send(f"{source}: данные отклонены — {exc}", key=f"{source}:rejected")
            overall = "rejected"
            continue
        except Exception as exc:  # noqa: BLE001 — сбой LFL не должен ронять другие источники
            session.rollback()
            log.exception("lfl %s failed", tid)
            _record(session, source, started, "error", {}, repr(exc))
            notifier.send(f"{source}: ошибка — {exc!r}", key=f"{source}:error")
            overall = "error"
            continue
        _record(session, source, started, "ok", result.counts, None)
        for warning in result.warnings:
            notifier.send(warning, key=f"warn:{warning}")
        all_tags |= result.tags
    revalidate(settings, all_tags)
    return overall


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
