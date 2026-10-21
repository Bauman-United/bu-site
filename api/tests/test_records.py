"""Рекордсмены клуба за всё время: суммы по всем сезонам, вместе с бывшими игроками."""

from datetime import UTC, datetime, timedelta

from bu_core.models import (
    Match,
    Player,
    PlayerSeasonStats,
    PlayerTournamentStats,
    Season,
    Tournament,
)
from sqlalchemy import delete, select


def _setup(db) -> None:
    db.execute(delete(PlayerSeasonStats))
    past = Season(slug="2019", label="2019")
    db.add(past)
    db.flush()
    by = {p.slug: p for p in db.scalars(select(Player))}
    current = db.scalars(select(Season).where(Season.slug == "2026")).one()
    veteran = Player(
        slug="staryy-veteran",
        first_name="Старый",
        last_name="Ветеран",
        position="FW",
        active=False,
        photo="https://st.joinsport.io/player/1/photo/a.jpg",
    )
    db.add(veteran)
    db.flush()
    rows = [
        # (игрок, сезон, игры, голы, передачи)
        (by["aleksandr-korolev"], current, 5, 3, 4),
        (by["aleksandr-korolev"], past, 10, 6, 1),  # всего 15 игр, 9 голов, 5 передач
        (veteran, past, 30, 9, 2),  # те же 9 голов, но игр больше → ниже Королёва
        (by["egor-kucha"], current, 20, 0, 5),  # 5 передач за 20 игр → ниже Королёва (15)
        (by["old-boy"], past, 1, 0, 0),
    ]
    for player, season, played, goals, assists in rows:
        db.add(
            PlayerSeasonStats(
                player_id=player.id,
                season_id=season.id,
                played=played,
                goals=goals,
                assists=assists,
            )
        )
    db.flush()


def test_all_time_records_sum_all_seasons_including_departed(client, db):
    _setup(db)
    r = client.get("/records/all-time").json()
    assert set(r) == {"goals", "assists", "played", "goalkeepers"}
    goals = [(x["rank"], x["slug"], x["value"]) for x in r["goals"]]
    # ничья по голам — выше тот, у кого меньше игр; нули в списки не попадают
    assert goals == [(1, "aleksandr-korolev", 9), (2, "staryy-veteran", 9)]
    assists = [(x["slug"], x["value"]) for x in r["assists"]]
    assert assists == [("aleksandr-korolev", 5), ("egor-kucha", 5), ("staryy-veteran", 2)]
    played = [(x["slug"], x["value"]) for x in r["played"]]
    assert played == [
        ("staryy-veteran", 30),
        ("egor-kucha", 20),
        ("aleksandr-korolev", 15),
        ("old-boy", 1),
    ]
    veteran = r["goals"][1]
    assert veteran == {
        "rank": 2,
        "slug": "staryy-veteran",
        "name": "Старый Ветеран",
        "photo": "https://st.joinsport.io/player/1/photo/a.jpg",
        "position": "FW",
        "value": 9,
        "played": 30,
        "active": False,
    }


def test_all_time_records_limit(client, db):
    _setup(db)
    r = client.get("/records/all-time", params={"limit": 1}).json()
    assert [x["slug"] for x in r["played"]] == ["staryy-veteran"]
    assert client.get("/records/all-time", params={"limit": 0}).status_code == 422


def test_all_time_records_empty_db(client, db):
    db.execute(delete(PlayerSeasonStats))
    db.flush()
    assert client.get("/records/all-time").json() == {
        "goals": [],
        "assists": [],
        "played": [],
        "goalkeepers": [],
    }


def test_goalkeeper_efficiency_only_over_ten_appearances(client, db):
    season = db.scalars(select(Season).where(Season.slug == "2026")).one()
    keepers = [
        Player(slug="keeper-a", first_name="Антон", last_name="Первый", position="GK"),
        Player(slug="keeper-b", first_name="Борис", last_name="Второй", position="GK"),
        Player(slug="keeper-short", first_name="Семён", last_name="Мало", position="GK"),
    ]
    db.add_all(keepers)
    db.flush()
    start = datetime(2020, 1, 1, tzinfo=UTC)
    for keeper_index, (keeper, games, conceded) in enumerate(
        ((keepers[0], 12, 9), (keepers[1], 11, 11), (keepers[2], 10, 0))
    ):
        keeper_tournament = Tournament(
            slug=f"keeper-tournament-{keeper_index}",
            name=f"Турнир вратаря {keeper_index}",
            short=f"ВР {keeper_index}",
            source="manual",
            external_id=f"keeper-tournament-{keeper_index}",
            season_id=season.id,
        )
        db.add(keeper_tournament)
        db.flush()
        db.add(
            PlayerTournamentStats(
                player_id=keeper.id,
                tournament_id=keeper_tournament.id,
                played=games,
            )
        )
        for index in range(games):
            goals = 1 if index < conceded else 0
            match = Match(
                slug=f"gk-{keeper.slug}-{index}",
                tournament_id=keeper_tournament.id,
                season_id=season.id,
                kickoff=start + timedelta(days=index),
                home=True,
                opponent_name=f"Соперник {index}",
                status="finished",
                score_us=2,
                score_them=goals,
                source="manual",
                external_id=f"gk-{keeper.slug}-{index}",
            )
            db.add(match)
    db.flush()

    rows = client.get("/records/all-time").json()["goalkeepers"]
    assert [(row["slug"], row["played"], row["conceded"], row["efficiency"]) for row in rows] == [
        ("keeper-a", 12, 9, 0.75),
        ("keeper-b", 11, 11, 1.0),
    ]
