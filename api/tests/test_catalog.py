def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_club_and_history(client):
    assert client.get("/club").json()["name"] == "Бауман Юнайтед"
    assert client.get("/history").json() == {"timeline": [], "trophies": [], "legends": []}


def test_history_returns_content_doc(client, db):
    from bu_core.models import ContentDoc

    timeline = [
        {"year": "Осень 2023", "tag": "BL", "title": "Победа в Кубке BL", "highlight": True}
    ]
    trophies = [{"place": 1, "title": "Кубок BL", "season": "Осень 2023"}]
    db.add(ContentDoc(key="history", data={"timeline": timeline, "trophies": trophies}))
    db.flush()
    assert client.get("/history").json() == {
        "timeline": timeline,
        "trophies": trophies,
        "legends": [],
    }


def test_seasons_and_tournaments(client):
    assert client.get("/seasons").json() == [
        {"slug": "2026-27", "label": "2026/27", "final_place": None}
    ]
    t = client.get("/tournaments", params={"season": "2026-27"}).json()
    assert t[0]["slug"] == "liga-inzhenerov" and t[0]["season"] == "2026-27"


def test_standings_default_current_season(client):
    data = client.get("/standings").json()
    assert data[0]["tournament"]["slug"] == "liga-inzhenerov"
    assert [r["pos"] for r in data[0]["rows"]] == [1, 6]
    assert data[0]["rows"][1]["is_us"] is True
    assert data[0]["source_url"] == "https://jf/tournament/1066703/tables"
