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
        "active": True,
        "photo_url": "https://st.joinsport.io/player/2079261/photo/68beabf36ef3a.jpg",
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


def test_match_without_timeline_but_with_goals_raises():
    import re

    html = re.sub(r'<div class="game-timeline__event [^>]*>', "<div>", read("match_5848533.html"))
    with pytest.raises(ParseError):
        parse_match(html)


def test_match_event_without_team_class_raises():
    html = read("match_5848533.html").replace(" team1 ", " ").replace(" team2 ", " ")
    with pytest.raises(ParseError):
        parse_match(html)


def test_calendar_unparseable_time_falls_back_to_midnight():
    html = read("calendar.html").replace(
        '<span class="blk-tcalendar__time">20:30</span>',
        '<span class="blk-tcalendar__time">--:--</span>',
        1,
    )
    entries = parse_calendar(html, date(2026, 9, 5), date(2026, 11, 22))
    assert len(entries) == 45


def test_application_player_photo_is_full_size():
    players = {p.full_name: p for p in parse_application(read("application.html"))}
    assert players["Королев Александр"].photo_url == (
        "https://st.joinsport.io/player/2079261/photo/68beabf36ef3a.jpg"
    )
    assert all(p.photo_url and "_60x60" not in p.photo_url for p in players.values())


def test_calendar_logos_are_full_size():
    entries = parse_calendar(read("calendar.html"), date(2026, 9, 5), date(2026, 11, 22))
    first = next(e for e in entries if e.external_id == "5848533")
    assert first.away_logo == "https://st.joinsport.io/team/1256048/logo/65fabe0d6e0ea.jpg"


def test_calendar_undated_units_yield_entries_without_kickoff():
    entries = parse_calendar(
        read("cup_calendar_undated.html"), date(2026, 9, 20), date(2026, 11, 28)
    )
    by_id = {e.external_id: e for e in entries}
    kvazar = by_id["5877228"]
    assert kvazar.kickoff is None
    assert {kvazar.home_name, kvazar.away_name} == {"Квазар", "Bauman United"}
    assert "1089660" in (kvazar.home_team_id, kvazar.away_team_id)
    assert kvazar.round == "Четвертьфинал"
    assert kvazar.home_score is None and kvazar.away_score is None
    # датированные матчи разбираются как раньше
    assert by_id["5877221"].kickoff == datetime(2026, 10, 4, 21, 30, tzinfo=MSK)
    assert any(e.kickoff is None for e in entries if e.external_id != "5877228")
