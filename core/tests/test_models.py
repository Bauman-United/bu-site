from datetime import UTC, datetime

from bu_core.models import Match, MatchEvent, Player, Season, Tournament
from sqlalchemy import select


def test_match_with_events_roundtrip(db):
    season = Season(slug="2026", label="2026")
    t = Tournament(
        slug="liga-inzhenerov-osen-2026",
        name="Лига Инженеров",
        short="ЛИ",
        source="joinfootball",
        external_id="1066703",
        season=season,
    )
    p = Player(slug="aleksandr-korolev", first_name="Александр", last_name="Королев")
    db.add_all([season, t, p])
    db.flush()
    m = Match(
        slug="2026-09-06-bauman-junior",
        tournament_id=t.id,
        season_id=season.id,
        kickoff=datetime(2026, 9, 6, 17, 30, tzinfo=UTC),
        home=True,
        opponent_name="Bauman Junior",
        status="finished",
        score_us=2,
        score_them=3,
        source="joinfootball",
        external_id="5848533",
    )
    m.events.append(MatchEvent(minute=22, type="goal", team="us", player_id=p.id))
    db.add(m)
    db.flush()

    loaded = db.scalars(select(Match).where(Match.slug == "2026-09-06-bauman-junior")).one()
    assert loaded.events[0].player_id == p.id
    assert loaded.tournament.season.slug == "2026"
    assert p.aliases == [] and p.manual_fields == []
