from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from bu_worker.sources.joinfootball.parse import (
    ParseError,
    parse_application,
    parse_calendar,
    parse_match,
    parse_standings,
    parse_tournament_info,
)

FIX = Path(__file__).parent / "fixtures" / "joinfootball"
MSK = ZoneInfo("Europe/Moscow")


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_tournament_info():
    info = parse_tournament_info(read("calendar.html"), "1066703", "https://x/tournament/1066703")
    assert info.name == "Лига Инженеров · Осень 2026"
    assert info.period_start == date(2026, 9, 5)
    assert info.period_end == date(2026, 11, 22)


def test_application_players():
    players = parse_application(read("application.html"))
    assert len(players) == 25
    korolev = next(p for p in players if p.full_name == "Королев Александр")
    assert korolev.model_dump() == {
        "external_id": "2079261",
        "full_name": "Королев Александр",
        "number": 10,
        "position": "MF",
        "played": 5,
        "goals": 2,
        "assists": 6,
        "yellow": 0,
        "red": 0,
    }


def test_application_player_without_number_and_dashes():
    players = {p.full_name: p for p in parse_application(read("application.html"))}
    assert players["Алексеев Александр"].number is None
    assert players["Алексеев Александр"].position == "DF"
    assert players["Алексеев Александр"].played == 2
    trifonov = players["Трифонов Матвей"]
    assert (trifonov.played, trifonov.goals, trifonov.yellow) == (0, 0, 0)


def test_calendar_all_matches_and_ours():
    entries = parse_calendar(read("calendar.html"), date(2026, 9, 5), date(2026, 11, 22))
    assert len(entries) == 45
    ours = [e for e in entries if "1089660" in (e.home_team_id, e.away_team_id)]
    assert len(ours) == 9
    first = next(e for e in ours if e.external_id == "5848533")
    assert first.kickoff == datetime(2026, 9, 6, 20, 30, tzinfo=MSK)
    assert (first.home_name, first.away_name) == ("Bauman United", "Bauman Junior")
    assert (first.home_score, first.away_score) == (2, 3)
    assert first.round == "1 тур"
    assert first.venue_name == "Металлург"
    assert first.venue_address == "Металлург, Россия, Москва, улица Новая Дорога, 11с1"
    future = next(e for e in ours if e.external_id == "5922873")
    assert future.home_score is None and future.away_team_id == "1089660"


def test_match_events_and_mvp():
    detail = parse_match(read("match_5848533.html"))
    assert len(detail.events) == 7
    first = detail.events[0]
    assert (first.minute, first.type, first.side, first.player_name) == (
        19,
        "goal",
        "away",
        "Горевой Александр",
    )
    set_piece = next(e for e in detail.events if e.minute == 25)
    assert (set_piece.type, set_piece.side, set_piece.note) == ("goal", "home", "со стандарта")
    with_assist = next(e for e in detail.events if e.minute == 46)
    assert with_assist.assist_name == "Микульский Николай"
    yellow = next(e for e in detail.events if e.minute == 43)
    assert (yellow.type, yellow.side, yellow.player_name) == ("yellow", "home", "Заночуев Михаил")
    assert (detail.mvp_name, detail.mvp_side) == ("Горевой Александр", "away")


def test_standings():
    rows = parse_standings(read("tables.html"))
    assert len(rows) == 10
    us = next(r for r in rows if r.team_name == "Bauman United")
    assert (us.pos, us.played, us.won, us.drawn, us.lost, us.gf, us.ga, us.pts) == (
        6,
        5,
        2,
        0,
        3,
        17,
        19,
        6,
    )
    assert rows[0].pos == 1


def test_broken_html_raises():
    with pytest.raises(ParseError):
        parse_application("<html><body>maintenance</body></html>")
    with pytest.raises(ParseError):
        parse_standings("<html></html>")
