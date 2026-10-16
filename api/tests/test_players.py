def test_active_players_ordered_with_season_stats(client):
    players = client.get("/players", params={"active": "true"}).json()
    assert [p["slug"] for p in players] == ["egor-kucha", "aleksandr-korolev"]
    assert players[1]["season"]["goals"] == 2
    assert "birth" not in str(players)


def test_players_can_be_filtered_by_tournament(client):
    players = client.get("/players", params={"tournament": "liga-inzhenerov"}).json()
    assert [p["slug"] for p in players] == ["egor-kucha", "aleksandr-korolev"]
    assert players[1]["season"]["assists"] == 6
    assert client.get("/players", params={"tournament": "unknown"}).json() == []


def test_player_detail(client):
    p = client.get("/players/aleksandr-korolev").json()
    assert p["nickname"] == "Король"
    assert p["total"]["assists"] == 6
    assert p["seasons"][0]["season"] == "2026-27"
    assert set(p["team_best"]) >= {"goals", "assists"}
    assert client.get("/players/nobody").status_code == 404


def test_player_detail_splits_stats_by_tournament(client, db):
    from bu_core.models import Player, PlayerTournamentStats, Season, Tournament
    from bu_core.recompute import recompute
    from sqlalchemy import select

    season = db.scalars(select(Season).where(Season.slug == "2026-27")).one()
    lfl = Tournament(
        slug="2-y-divizion-a",
        name="2-й дивизион А · ВЛ-2026",
        short="2-й дивизион А",
        source="lfl",
        external_id="32573",
        season_id=season.id,
    )
    db.add(lfl)
    db.flush()
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    db.add(
        PlayerTournamentStats(
            player_id=korolev.id,
            tournament_id=lfl.id,
            played=24,
            goals=12,
            assists=22,
            yellow=3,
            red=1,
        )
    )
    db.flush()
    recompute(db)

    p = client.get("/players/aleksandr-korolev").json()
    rows = {r["tournament"]["slug"]: r["stats"] for r in p["tournaments"]}
    assert rows["liga-inzhenerov"]["goals"] == 2 and rows["liga-inzhenerov"]["played"] == 5
    assert rows["2-y-divizion-a"]["goals"] == 12 and rows["2-y-divizion-a"]["red"] == 1
    assert p["season"]["goals"] == 14  # общая статистика сезона = сумма турниров
    assert p["tournaments"][0]["season"] == "2026-27"
