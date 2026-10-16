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
