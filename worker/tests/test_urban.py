"""Urban Cup (urban-cup.ru) — ещё одна лига на платформе joinsport.

Турниры там многоэтапные (группы, отборочные раунды, плей-офф): календарь турнира
по умолчанию показывает один этап, где нашей команды может не быть. Тогда матчи берём
из календаря команды за сезон (/team/<id>/calendar?season_id=…).
"""

from datetime import date, datetime
from pathlib import Path

import httpx
import pytest
from bu_core.models import IngestRun, Match, StandingRow, Tournament
from bu_core.settings import JoinsportSource, Settings
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import history_sources, run_history, source_spec
from bu_worker.sources.joinfootball.discover import (
    discover_tournament_seasons,
    parse_season_ids,
    parse_season_tournament_ids,
)
from bu_worker.sources.joinfootball.fetch import fetch_bundle
from bu_worker.sources.joinfootball.parse import (
    MSK,
    ParseError,
    is_multi_stage,
    parse_application,
    parse_calendar,
    parse_team_calendar,
    parse_tournament_info,
)
from sqlalchemy import select

URB = Path(__file__).parent / "fixtures" / "urban"
JF = Path(__file__).parent / "fixtures" / "joinfootball"
TEAM = "1321682"
SEASON = "10124927"  # 2023/24: «Лига Чемпионов 23/24» и «Будняя лига/Весна 2024»
FUTURE = date(2030, 1, 1)


def read(name: str) -> str:
    return (URB / name).read_text(encoding="utf-8")


def info():
    return parse_tournament_info(
        read("tournament_1033502_calendar.html"), "1033502", "https://u/tournament/1033502"
    )


def test_default_settings_have_urban_source():
    s = Settings(_env_file=None)
    spec = source_spec(s, "urban")
    assert (spec.base, spec.team_id, spec.current_ids) == ("https://urban-cup.ru", TEAM, [])
    assert [j.key for j in s.joinsport_sources] == ["joinfootball", "ifl", "urban"]
    assert history_sources(s) == ("joinfootball", "ifl", "urban", "lfl")


def test_bl_and_ifl_specs_unchanged():
    s = Settings(_env_file=None)
    bl = source_spec(s, "joinfootball")
    assert (bl.base, bl.team_id) == ("https://bauman_league.join.football", "1089660")
    assert "1067299" in bl.current_ids
    ifl = source_spec(s, "ifl")
    assert (ifl.base, ifl.team_id, ifl.current_ids) == ("https://ifl-bmstu.ru", "1003070", [])


def test_urban_seasons_and_tournaments():
    seasons = parse_season_ids(read("team_calendar.html"), TEAM)
    assert len(seasons) == 19 and seasons[0] == "10128098" and SEASON in seasons
    assert parse_season_tournament_ids(read("team_calendar.html")) == []  # 2025/26 — пусто
    assert parse_season_tournament_ids(read("team_season_10124927.html")) == [
        "1033502",
        "1036985",
    ]


def test_calendar_grouped_by_tours_takes_date_from_match_time():
    entries = parse_calendar(read("tournament_1033502_calendar.html"), **_period())
    assert len(entries) == 6
    assert entries[0].kickoff == datetime(2023, 11, 26, 11, 0, tzinfo=MSK)
    assert all(TEAM not in (e.home_team_id, e.away_team_id) for e in entries)  # другой этап


def _period() -> dict:
    i = info()
    return {"period_start": i.period_start, "period_end": i.period_end}


def test_team_calendar_gives_our_matches_of_one_tournament():
    entries = parse_team_calendar(read("team_season_10124927.html"), "1033502", **_period())
    assert len(entries) == 3
    first = entries[0]
    assert first.kickoff == datetime(2023, 10, 11, 20, 30, tzinfo=MSK)
    assert (first.home_team_id, first.home_name, first.away_name) == (
        TEAM,
        "Bauman United",
        "Автобус 2.0",
    )
    assert (first.home_score, first.away_score, first.external_id) == (6, 1, "3553605")
    assert first.venue_name == "Локомотив (поле 4)"


def test_urban_application_parses():
    players = parse_application(read("tournament_1033502_application.html"), departed=True)
    assert len(players) == 27


def urban_site() -> PoliteClient:
    pages = {
        "/tournament/1033502/calendar": "tournament_1033502_calendar.html",
        "/tournament/1033502/teams/application": "tournament_1033502_application.html",
        "/tournament/1033502/tables": "tournament_1033502_tables.html",
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(str(request.url.raw_path, "ascii"))
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /matches\n")
        if path == f"/team/{TEAM}/calendar":
            season = request.url.params.get("season_id")
            name = "team_season_10124927.html" if season == SEASON else "team_calendar.html"
            return httpx.Response(200, text=read(name))
        if path in pages:
            return httpx.Response(200, text=read(pages[path]))
        if path.startswith("/match/"):
            return httpx.Response(200, text=(JF / "match_5848533.html").read_text("utf-8"))
        return httpx.Response(404)

    client = PoliteClient(
        "https://urban.test", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )
    client.seen = seen  # type: ignore[attr-defined]
    return client


def test_discover_keeps_season_of_each_tournament():
    found = discover_tournament_seasons(urban_site(), TEAM)
    assert found == {"1033502": SEASON, "1036985": SEASON}


def test_history_urban_multi_stage_tournament(db, tmp_path):
    s = Settings(
        _env_file=None,
        snapshot_dir=str(tmp_path / "snap"),
        joinsport_leagues=[
            JoinsportSource(key="urban", title="Urban Cup", base="https://urban.test", team_id=TEAM)
        ],
    )
    client = urban_site()
    status = run_history(
        db, s, {"urban": client}, Notifier(None, None), sources=["urban"], limit=1, today=FUTURE
    )
    assert status == "ok"
    runs = {r.source: r.status for r in db.scalars(select(IngestRun))}
    assert runs == {"urban:1033502": "ok"}
    t = db.scalars(select(Tournament)).one()
    assert (t.source, t.name) == ("urban", "Лига Чемпионов 23/24")
    matches = db.scalars(select(Match)).all()
    assert len(matches) == 3 and all(m.source == "urban" for m in matches)
    # в таблице по умолчанию — чужая группа: её не сохраняем
    assert db.scalars(select(StandingRow)).all() == []
    assert f"/team/{TEAM}/calendar?season_id={SEASON}" in client.seen  # type: ignore[attr-defined]


def test_stage_selector_marks_multi_stage_calendar():
    assert is_multi_stage(read("tournament_1032591_calendar.html"))
    assert not is_multi_stage((JF / "calendar.html").read_text(encoding="utf-8"))
    assert not is_multi_stage((JF / "cup_calendar.html").read_text(encoding="utf-8"))


def test_multi_stage_adds_group_matches_from_team_calendar():
    """Календарь турнира показывает плей-офф (1 наш матч); групповые — в календаре команды."""
    pages = {
        "/tournament/1032591/calendar": "tournament_1032591_calendar.html",
        "/tournament/1032591/teams/application": "tournament_1033502_application.html",
        "/tournament/1032591/tables": "tournament_1032591_tables.html",
        f"/team/{TEAM}/calendar": "team_season_10125962.html",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path in pages:
            return httpx.Response(200, text=read(pages[request.url.path]))
        return httpx.Response(200, text=(JF / "match_5848533.html").read_text("utf-8"))

    client = PoliteClient(
        "https://urban.test", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )
    path = f"/team/{TEAM}/calendar?season_id=10125962"
    bundle = fetch_bundle(client, "1032591", TEAM, "https://u", lambda *_: None, FUTURE, path)
    assert bundle.multi_stage and bundle.standings == []  # вместо таблицы — сетка плей-офф
    assert len(bundle.calendar) == 14  # 13 групповых + 1 плей-офф
    assert len({e.external_id for e in bundle.calendar}) == 14
    assert all(TEAM in (e.home_team_id, e.away_team_id) for e in bundle.calendar)
    # без календаря команды (обычный текущий запуск) — как раньше: нет таблицы → ошибка
    with pytest.raises(ParseError):
        fetch_bundle(client, "1032591", TEAM, "https://u", lambda *_: None)
