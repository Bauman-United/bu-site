from datetime import UTC, datetime

from bu_core.models import (
    Computed,
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    Player,
    PlayerSeasonStats,
    PlayerTournamentStats,
    Season,
    Tournament,
)
from bu_core.recompute import recompute


def test_recompute_mixes_sources(db):
    season = Season(slug="2026-27", label="2026/27")
    jf = Tournament(
        slug="li",
        name="Лига Инженеров",
        short="ЛИ",
        source="joinfootball",
        external_id="1",
        season=season,
    )
    manual = Tournament(slug="lfl", name="ЛФЛ", short="ЛФЛ", source="manual", season=season)
    p = Player(
        slug="a-k",
        first_name="А",
        last_name="К",
        number=7,
        photo="https://lfl.ru/a-k.jpg",
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    db.add_all([season, jf, manual, p])
    db.flush()
    db.add(
        PlayerTournamentStats(
            player_id=p.id, tournament_id=jf.id, played=5, goals=2, assists=6, yellow=1, red=0
        )
    )
    m1 = Match(
        slug="m1",
        tournament_id=jf.id,
        season_id=season.id,
        home=True,
        kickoff=datetime(2026, 9, 6, tzinfo=UTC),
        opponent_name="X",
        status="finished",
        score_us=2,
        score_them=0,
        source="joinfootball",
        external_id="1",
        mvp_player_id=p.id,
    )
    m2 = Match(
        slug="m2",
        tournament_id=manual.id,
        season_id=season.id,
        home=False,
        kickoff=datetime(2026, 10, 11, tzinfo=UTC),
        opponent_name="Y",
        status="finished",
        score_us=1,
        score_them=1,
        source="manual",
    )
    m2.events.append(MatchEvent(minute=4, type="goal", team="us", player_id=p.id))
    db.add_all([m1, m2])
    db.flush()
    m1.events.append(MatchEvent(minute=9, type="goal", team="us", player_id=p.id))
    db.add(MatchAppearance(match_id=m2.id, player_id=p.id))
    db.add(ContentDoc(key="club", data={"founded": 2019}))
    db.add(ContentDoc(key="history", data={"trophies": [{"place": 1}, {"place": 2}]}))
    db.flush()

    recompute(db)

    line = db.get(PlayerSeasonStats, (p.id, season.id))
    assert (line.played, line.goals, line.assists, line.yellow, line.mvp) == (6, 3, 6, 1, 1)
    assert db.get(Computed, "meta").data == {"current_season": "2026-27"}
    season_doc = db.get(Computed, "season:2026-27").data
    assert [f["outcome"] for f in season_doc["form"]] == ["W", "D"]
    assert season_doc["leaders"]["goals"][0]["slug"] == "a-k"
    assert season_doc["leaders"]["goals"][0]["photo"] == "https://lfl.ru/a-k.jpg"
    assert season_doc["leaders"]["goals"][0]["number"] == 7
    club = db.get(Computed, "club").data
    assert club["numbers"] == {"founded": 2019, "matches": 2, "goals": 3, "trophies": 1}
    assert club["records"]["fastest_goal"] == {"slug": "m2", "minute": 4}


def test_recompute_empty_db(db):
    recompute(db)
    assert db.get(Computed, "meta").data == {"current_season": None}


def test_recompute_tolerates_undated_matches(db):
    season = Season(slug="2026-27", label="2026/27")
    later = Season(slug="2027-28", label="2027/28")
    cup = Tournament(slug="cup", name="Кубок", short="Кубок", source="manual", season=season)
    next_cup = Tournament(slug="cup2", name="Кубок", short="Кубок", source="manual", season=later)
    db.add_all([season, later, cup, next_cup])
    db.flush()
    common = dict(home=True, source="manual")
    db.add_all(
        [
            Match(
                slug="played",
                tournament_id=cup.id,
                season_id=season.id,
                kickoff=datetime(2026, 9, 6, tzinfo=UTC),
                opponent_name="X",
                status="finished",
                score_us=1,
                score_them=0,
                **common,
            ),
            Match(  # без даты, но со счётом (дата так и не появилась на сайте лиги)
                slug="undated-finished",
                tournament_id=cup.id,
                season_id=season.id,
                kickoff=None,
                opponent_name="Z",
                status="finished",
                score_us=0,
                score_them=2,
                **common,
            ),
            Match(
                slug="undated",
                tournament_id=next_cup.id,
                season_id=later.id,
                kickoff=None,
                opponent_name="Квазар",
                status="scheduled",
                **common,
            ),
        ]
    )
    db.flush()

    recompute(db)

    assert db.get(Computed, "meta").data == {"current_season": "2026-27"}
    form = db.get(Computed, "season:2026-27").data["form"]
    assert [f["slug"] for f in form] == ["played", "undated-finished"]


def test_recompute_only_undated_matches(db):
    season = Season(slug="2026-27", label="2026/27")
    cup = Tournament(slug="cup", name="Кубок", short="Кубок", source="manual", season=season)
    db.add_all([season, cup])
    db.flush()
    db.add(
        Match(
            slug="undated",
            tournament_id=cup.id,
            season_id=season.id,
            kickoff=None,
            home=True,
            opponent_name="Квазар",
            status="scheduled",
            source="manual",
        )
    )
    db.flush()
    recompute(db)
    assert db.get(Computed, "meta").data == {"current_season": "2026-27"}
