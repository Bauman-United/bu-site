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
        {"slug": "2026", "label": "2026", "final_place": None, "current": True}
    ]
    t = client.get("/tournaments", params={"season": "2026"}).json()
    assert t[0]["slug"] == "liga-inzhenerov" and t[0]["season"] == "2026"


def test_seasons_mark_current_not_newest(client, db):
    """Будущий сезон (турнир с матчами только впереди) не становится текущим."""
    from datetime import UTC, datetime

    from bu_core.models import Match, Season, Tournament
    from bu_core.recompute import recompute

    later = Season(slug="2099", label="2099")
    cup = Tournament(slug="cup-2099", name="Кубок", short="Кубок", source="manual", season=later)
    db.add_all([later, cup])
    db.flush()
    db.add(
        Match(
            slug="future",
            tournament_id=cup.id,
            season_id=later.id,
            home=True,
            kickoff=datetime(2099, 3, 1, tzinfo=UTC),
            opponent_name="X",
            status="scheduled",
            source="manual",
        )
    )
    db.flush()
    recompute(db)
    seasons = client.get("/seasons").json()
    assert [(s["slug"], s["current"]) for s in seasons] == [("2099", False), ("2026", True)]


def test_standings_default_current_season(client):
    data = client.get("/standings").json()
    assert data[0]["tournament"]["slug"] == "liga-inzhenerov"
    assert [r["pos"] for r in data[0]["rows"]] == [1, 6]
    assert data[0]["rows"][1]["is_us"] is True
    assert data[0]["source_url"] == "https://jf/tournament/1066703/tables"
