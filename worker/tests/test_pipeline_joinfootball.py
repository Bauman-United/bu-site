from datetime import UTC, datetime
from pathlib import Path

import pytest
from bu_core.models import (
    IngestRun,
    Match,
    MatchEvent,
    Player,
    PlayerTournamentStats,
    StandingRow,
)
from bu_worker.dto import JoinFootballBundle
from bu_worker.pipeline.joinfootball import SanityError, ingest, sanity_check
from bu_worker.sources.joinfootball.parse import (
    parse_application,
    parse_calendar,
    parse_match,
    parse_standings,
    parse_tournament_info,
)
from sqlalchemy import func, select

FIX = Path(__file__).parent / "fixtures" / "joinfootball"
TEAM = "1089660"
NAMES = ["Bauman United"]


def bundle() -> JoinFootballBundle:
    read = lambda n: (FIX / n).read_text(encoding="utf-8")  # noqa: E731
    info = parse_tournament_info(read("calendar.html"), "1066703", "https://x/tournament/1066703")
    calendar = [
        e
        for e in parse_calendar(read("calendar.html"), info.period_start, info.period_end)
        if TEAM in (e.home_team_id, e.away_team_id)
    ]
    return JoinFootballBundle(
        tournament=info,
        players=parse_application(read("application.html")),
        calendar=calendar,
        details={"5848533": parse_match(read("match_5848533.html"))},
        standings=parse_standings(read("tables.html")),
    )


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_ingest_creates_everything(db):
    result = ingest(db, bundle(), TEAM, NAMES)
    assert count(db, Player) == 25
    assert count(db, Match) == 9
    assert count(db, StandingRow) == 10
    assert result.counts == {"players": 25, "matches": 9, "standings": 10}
    assert "matches" in result.tags and "player:aleksandr-korolev" in result.tags

    m = db.scalars(select(Match).where(Match.external_id == "5848533")).one()
    assert m.slug == "2026-09-06-bauman-junior"
    assert (m.home, m.score_us, m.score_them, m.status) == (True, 2, 3, "finished")
    assert m.tournament.season.slug == "2026-27"
    ours = [e for e in m.events if e.team == "us"]
    assert {e.player_name for e in ours if e.type == "goal"} == {
        "Королев Александр",
        "Колочков Кирилл",
    }
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    assert any(e.player_id == korolev.id for e in ours)
    assert m.mvp_player_id is None  # MVP матча — игрок соперника

    stats = db.get(PlayerTournamentStats, (korolev.id, m.tournament_id))
    assert (stats.played, stats.goals, stats.assists) == (5, 2, 6)
    us_row = db.scalars(select(StandingRow).where(StandingRow.is_us)).one()
    assert us_row.pos == 6


def test_ingest_is_idempotent(db):
    ingest(db, bundle(), TEAM, NAMES)
    ingest(db, bundle(), TEAM, NAMES)
    assert count(db, Player) == 25
    assert count(db, Match) == 9
    assert count(db, MatchEvent) == 7
    assert count(db, StandingRow) == 10


def test_away_match_is_mirrored(db):
    ingest(db, bundle(), TEAM, NAMES)
    away = db.scalars(select(Match).where(Match.external_id == "5922873")).one()
    assert away.home is False
    assert away.opponent_name == "Мессия"
    assert away.status == "scheduled" and away.score_us is None


def test_manual_fields_win(db):
    ingest(db, bundle(), TEAM, NAMES)
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    korolev.number = 7
    korolev.manual_fields = ["number"]
    db.flush()
    ingest(db, bundle(), TEAM, NAMES)
    db.refresh(korolev)
    assert korolev.number == 7


def test_sanity_rejects_shrunk_data(db):
    good = bundle()
    db.add(
        IngestRun(
            source="joinfootball:1066703",
            started_at=datetime.now(UTC),
            status="ok",
            counts={"players": 25, "matches": 9, "standings": 10},
        )
    )
    db.flush()
    sanity_check(db, "joinfootball:1066703", good)  # не бросает
    shrunk = good.model_copy(update={"players": good.players[:5]})
    with pytest.raises(SanityError):
        sanity_check(db, "joinfootball:1066703", shrunk)
    empty = good.model_copy(update={"standings": []})
    with pytest.raises(SanityError):
        sanity_check(db, "joinfootball:1066703", empty)


def test_empty_detail_does_not_wipe_events_or_mvp(db):
    ingest(db, bundle(), TEAM, NAMES)
    m = db.scalars(select(Match).where(Match.external_id == "5848533")).one()
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    m.mvp_player_id = korolev.id
    db.flush()
    from bu_worker.dto import MatchDetail

    empty = bundle().model_copy(update={"details": {"5848533": MatchDetail(events=[])}})
    ingest(db, empty, TEAM, NAMES)
    db.refresh(m)
    assert len(m.events) == 7
    assert m.mvp_player_id == korolev.id


def test_manual_mvp_and_events_survive_scrape(db):
    ingest(db, bundle(), TEAM, NAMES)
    m = db.scalars(select(Match).where(Match.external_id == "5848533")).one()
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    m.mvp_player_id = korolev.id
    m.events.clear()
    db.flush()
    m.events.append(MatchEvent(minute=1, type="goal", team="us", player_id=korolev.id))
    m.manual_fields = ["mvp", "events"]
    db.flush()
    ingest(db, bundle(), TEAM, NAMES)
    db.refresh(m)
    assert m.mvp_player_id == korolev.id
    assert [e.minute for e in m.events] == [1]


def test_standings_shrink_is_rejected(db):
    good = bundle()
    db.add(
        IngestRun(
            source="joinfootball:1066703",
            started_at=datetime.now(UTC),
            status="ok",
            counts={"players": 25, "matches": 9, "standings": 10},
        )
    )
    db.flush()
    with pytest.raises(SanityError):
        sanity_check(
            db, "joinfootball:1066703", good.model_copy(update={"standings": good.standings[:7]})
        )


def test_namesakes_are_not_merged(db):
    b = bundle()
    twin = b.players[0].model_copy(update={"external_id": "999999"})
    result = ingest(db, b.model_copy(update={"players": [*b.players, twin]}), TEAM, NAMES)
    assert count(db, Player) == 25
    assert any(twin.full_name in w for w in result.warnings)


def test_departed_players_become_inactive(db):
    b = bundle()
    ingest(db, b, TEAM, NAMES)
    gone = b.players[-1]
    ingest(db, b.model_copy(update={"players": b.players[:-1]}), TEAM, NAMES)
    from bu_core.models import PlayerSourceLink

    link = db.scalars(
        select(PlayerSourceLink).where(PlayerSourceLink.external_id == gone.external_id)
    ).one()
    assert db.get(Player, link.player_id).active is False


def test_player_photo_from_source_unless_manual(db):
    ingest(db, bundle(), TEAM, NAMES)
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    assert korolev.photo == "https://st.joinsport.io/player/2079261/photo/68beabf36ef3a.jpg"
    korolev.photo = "/media/players/korolev.webp"
    korolev.manual_fields = ["photo"]
    db.flush()
    ingest(db, bundle(), TEAM, NAMES)
    db.refresh(korolev)
    assert korolev.photo == "/media/players/korolev.webp"


def cup_bundle(calendar_html: str | None = None) -> JoinFootballBundle:
    read = lambda n: (FIX / n).read_text(encoding="utf-8")  # noqa: E731
    html = calendar_html if calendar_html is not None else read("cup_calendar_undated.html")
    info = parse_tournament_info(html, "1067299", "https://x/tournament/1067299")
    calendar = [
        e
        for e in parse_calendar(html, info.period_start, info.period_end)
        if TEAM in (e.home_team_id, e.away_team_id)
    ]
    return JoinFootballBundle(
        tournament=info,
        players=parse_application(read("cup_application.html")),
        calendar=calendar,
        details={},
        standings=[],
    )


def kvazar(db) -> Match:
    return db.scalars(select(Match).where(Match.external_id == "5877228")).one()


def test_undated_match_is_ingested(db):
    result = ingest(db, cup_bundle(), TEAM, NAMES)
    m = kvazar(db)
    assert m.kickoff is None
    assert m.slug == "kvazar-5877228"
    assert (m.opponent_name, m.status, m.round) == ("Квазар", "scheduled", "Четвертьфинал")
    assert "match:kvazar-5877228" in result.tags


def test_undated_match_gets_date_later_and_keeps_slug(db):
    ingest(db, cup_bundle(), TEAM, NAMES)
    m = kvazar(db)
    m.kickoff = datetime(2026, 10, 25, 18, 30, tzinfo=UTC)
    db.flush()
    ingest(db, cup_bundle(), TEAM, NAMES)  # снова «Не задано» — известную дату не стираем
    db.refresh(m)
    assert m.kickoff == datetime(2026, 10, 25, 18, 30, tzinfo=UTC)

    dated = cup_bundle()
    entry = next(e for e in dated.calendar if e.external_id == "5877228")
    entry.kickoff = datetime(2026, 11, 1, 17, 0, tzinfo=UTC)
    ingest(db, dated, TEAM, NAMES)
    db.refresh(m)
    assert m.kickoff == datetime(2026, 11, 1, 17, 0, tzinfo=UTC)
    assert m.slug == "kvazar-5877228"


def test_manual_kickoff_and_venue_survive_scrape(db):
    ingest(db, cup_bundle(), TEAM, NAMES)
    m = kvazar(db)
    m.kickoff = datetime(2026, 10, 25, 18, 30, tzinfo=UTC)
    m.venue_name, m.venue_address = "Свой стадион", "Москва"
    m.manual_fields = ["kickoff", "venue"]
    db.flush()
    dated = cup_bundle()
    entry = next(e for e in dated.calendar if e.external_id == "5877228")
    entry.kickoff = datetime(2026, 11, 1, 17, 0, tzinfo=UTC)
    entry.venue_name, entry.venue_address = "Металлург", "Новая Дорога"
    ingest(db, dated, TEAM, NAMES)
    db.refresh(m)
    assert m.kickoff == datetime(2026, 10, 25, 18, 30, tzinfo=UTC)
    assert (m.venue_name, m.venue_address) == ("Свой стадион", "Москва")
