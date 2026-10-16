"""История: поиск прошлых турниров (БЛ, IFL, ЛФЛ), архив, загрузка прошлых сезонов."""

from datetime import date
from pathlib import Path

import httpx
from bu_core.models import IngestRun, Match, Player, PlayerTournamentStats, Tournament
from bu_core.settings import JoinsportSource, Settings
from bu_worker.dto import JoinFootballBundle
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.pipeline.joinfootball import ingest, is_archived
from bu_worker.runner import run_history, run_joinfootball
from bu_worker.sources.joinfootball.discover import (
    discover_tournaments,
    parse_season_ids,
    parse_season_tournament_ids,
)
from bu_worker.sources.joinfootball.parse import (
    parse_application,
    parse_calendar,
    parse_standings,
    parse_tournament_info,
)
from bu_worker.sources.lfl.parse import parse_club_tournament_ids
from sqlalchemy import select

HIST = Path(__file__).parent / "fixtures" / "history"
FIX = Path(__file__).parent / "fixtures" / "joinfootball"
FUTURE = date(2030, 1, 1)  # все турниры фикстур (осень 2026) уже в прошлом


TEAM = "1089660"
NAMES = ["Bauman United"]


def bundle() -> JoinFootballBundle:
    html = (FIX / "calendar.html").read_text(encoding="utf-8")
    info = parse_tournament_info(html, "1066703", "https://x/tournament/1066703")
    return JoinFootballBundle(
        tournament=info,
        players=parse_application((FIX / "application.html").read_text(encoding="utf-8")),
        calendar=[
            e
            for e in parse_calendar(html, info.period_start, info.period_end)
            if TEAM in (e.home_team_id, e.away_team_id)
        ],
        details={},
        standings=parse_standings((FIX / "tables.html").read_text(encoding="utf-8")),
    )


def read(name: str) -> str:
    return (HIST / name).read_text(encoding="utf-8")


# --- поиск турниров -------------------------------------------------------


def test_bl_season_list_newest_first():
    ids = parse_season_ids(read("bl_team_calendar.html"), "1089660")
    assert len(ids) == 19
    assert ids[0] == "10131604"  # Осень 2026
    assert ids[-1] == "1000327"  # Осень 2015
    assert "1003416" in ids


def test_ifl_season_list():
    ids = parse_season_ids(read("ifl_team_calendar.html"), "1003070")
    assert len(ids) == 20 and ids[-1] == "1000089"  # Осень 2016


def test_season_tournaments_come_from_matches_not_sidebar():
    # в сайдбаре каждой страницы — текущие турниры лиги (1066703, 1066706, 1066740, 1067299)
    assert parse_season_tournament_ids(read("bl_season_1003416.html")) == ["1006198"]
    assert parse_season_tournament_ids(read("bl_team_calendar.html")) == ["1066703", "1067299"]
    assert parse_season_tournament_ids(read("ifl_team_calendar.html")) == []


def test_lfl_club_tournaments_skip_test_and_non_numeric():
    ids = parse_club_tournament_ids(read("lfl_club_tournaments.html"))
    assert ids == ["32573", "33238", "23472", "27997", "28648"]


def joinsport_site(seasons: dict[str, str], default: str = "bl_team_calendar.html") -> PoliteClient:
    """Фейковый joinsport: /team/…/calendar?season_id=… → файл из fixtures/history."""
    pages = {
        "/tournament/1066703/calendar": FIX / "calendar.html",
        "/tournament/1066703/teams/application": FIX / "application.html",
        "/tournament/1066703/tables": FIX / "tables.html",
        "/tournament/1067299/calendar": FIX / "cup_calendar.html",
        "/tournament/1067299/teams/application": FIX / "cup_application.html",
        "/tournament/1067299/tables": FIX / "cup_tables.html",
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(str(request.url.raw_path, "ascii"))
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /matches\n")
        if path.endswith("/calendar") and path.startswith("/team/"):
            season = request.url.params.get("season_id")
            name = seasons.get(season or "", default)
            return httpx.Response(200, text=read(name))
        if path in pages:
            return httpx.Response(200, text=pages[path].read_text(encoding="utf-8"))
        if path.startswith("/match/"):
            return httpx.Response(200, text=(FIX / "match_5848533.html").read_text("utf-8"))
        return httpx.Response(404)

    client = PoliteClient(
        "https://jf.test", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )
    client.seen = seen  # type: ignore[attr-defined]
    return client


def test_discover_bl_tournaments_oldest_first():
    client = joinsport_site(
        {
            "": "bl_team_calendar.html",  # без season_id — текущий сезон и список сезонов
            "1003416": "bl_season_1003416.html",
            "10131604": "bl_team_calendar.html",
        },
        default="ifl_team_calendar.html",  # прочие сезоны — без матчей
    )
    tids = discover_tournaments(client, "1089660")  # первая страница — список сезонов
    assert tids == ["1006198", "1066703", "1067299"]
    calendars = [p for p in client.seen if p.startswith("/team/")]  # type: ignore[attr-defined]
    assert len(calendars) == 1 + 19  # список сезонов + страница каждого сезона


# --- прошлые турниры: игроки, архив ---------------------------------------


def test_past_tournament_does_not_touch_current_squad(db):
    ingest(db, bundle(), TEAM, NAMES)  # текущий сезон: игрок с номером
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    korolev.number, korolev.active = 77, True
    newbie = bundle()
    newbie.players[0] = newbie.players[0].model_copy(
        update={"external_id": "999", "full_name": "Старый Ветеран", "number": 5}
    )
    db.flush()
    ingest(db, newbie, TEAM, NAMES, today=FUTURE)  # тот же турнир, но уже в прошлом
    db.refresh(korolev)
    assert (korolev.number, korolev.active) == (77, True)
    veteran = db.scalars(select(Player).where(Player.last_name == "Старый")).one()
    assert veteran.active is False  # бывший игрок: в общий состав не попадает
    tid = db.scalars(select(Tournament.id).where(Tournament.external_id == "1066703")).one()
    assert db.get(PlayerTournamentStats, (veteran.id, tid)) is not None


def test_period_end_is_stored(db):
    ingest(db, bundle(), TEAM, NAMES)
    t = db.scalars(select(Tournament)).one()
    assert t.period_end == date(2026, 11, 22)


def test_archived_needs_old_period_and_ok_run(db):
    ingest(db, bundle(), TEAM, NAMES)
    assert not is_archived(db, "joinfootball", "1066703", FUTURE)  # ещё ни одного ok-запуска
    db.add(
        IngestRun(
            source="joinfootball:1066703", started_at=FUTURE, status="ok", counts={}, error=None
        )
    )
    db.flush()
    assert is_archived(db, "joinfootball", "1066703", FUTURE)
    assert not is_archived(db, "joinfootball", "1066703", date(2026, 12, 1))  # < 14 дней
    assert not is_archived(db, "ifl", "1066703", FUTURE)  # другой источник


def settings(tmp_path, ifl_team_id: str = "1003070", **kw) -> Settings:
    return Settings(
        _env_file=None,
        snapshot_dir=str(tmp_path / "snap"),
        joinfootball_base="https://jf.test",
        joinsport_leagues=[
            JoinsportSource(key="ifl", title="IFL", base="https://jf.test", team_id=ifl_team_id)
        ],
        **kw,
    )


def test_archived_tournament_is_not_refetched(db, tmp_path):
    s = settings(tmp_path, joinfootball_tournament_ids=["1066703"])
    first = joinsport_site({})
    assert run_joinfootball(db, s, first, Notifier(None, None), today=FUTURE) == "ok"
    second = joinsport_site({})
    assert run_joinfootball(db, s, second, Notifier(None, None), today=FUTURE) == "ok"
    assert [p for p in second.seen if "/tournament/" in p] == []  # type: ignore[attr-defined]
    forced = joinsport_site({})
    run_joinfootball(db, s, forced, Notifier(None, None), today=FUTURE, refresh=True)
    assert any("/tournament/1066703" in p for p in forced.seen)  # type: ignore[attr-defined]


def test_history_ifl_uses_own_source_key(db, tmp_path):
    s = settings(tmp_path, joinfootball_tournament_ids=[], ifl_team_id="1089660")
    client = joinsport_site({})
    status = run_history(
        db, s, {"ifl": client}, Notifier(None, None), sources=["ifl"], today=FUTURE
    )
    assert status == "ok"
    runs = {r.source: r.status for r in db.scalars(select(IngestRun))}
    assert runs == {"ifl:1066703": "ok", "ifl:1067299": "ok"}
    assert {t.source for t in db.scalars(select(Tournament))} == {"ifl"}
    assert all(m.source == "ifl" for m in db.scalars(select(Match)))
    assert all(not p.active for p in db.scalars(select(Player)))  # всё — прошлые турниры


def test_history_limit_and_skips_current_ids(db, tmp_path):
    s = settings(tmp_path, joinfootball_tournament_ids=["1067299"])
    client = joinsport_site({})
    run_history(
        db,
        s,
        {"joinfootball": client},
        Notifier(None, None),
        sources=["joinfootball"],
        limit=1,
        today=FUTURE,
    )
    # 1067299 — текущий турнир из настроек, его ведёт обычный запуск раз в 6 часов
    assert [r.source for r in db.scalars(select(IngestRun))] == ["joinfootball:1066703"]


def test_ifl_application_parses():
    players = {p.full_name: p for p in parse_application(read("ifl_application.html"))}
    assert len(players) == 21  # вкладка «Заявка команды»
    assert players["Медведев Владимир"].goals == 17  # «17 (1)» — голы (из них с пенальти)


def test_departed_players_for_past_tournaments():
    players = parse_application(read("ifl_application.html"), departed=True)
    assert len(players) == 24
    gone = [p for p in players if not p.active]
    assert [p.full_name for p in gone][0] == "Фролов Юрий" and len(gone) == 3
