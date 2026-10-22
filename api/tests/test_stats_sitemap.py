def test_stats_current_and_all(client):
    s = client.get("/stats").json()
    assert s["season"] == "2026"
    assert s["leaders"]["goals"][0]["slug"] == "aleksandr-korolev"
    row = next(p for p in s["players"] if p["slug"] == "aleksandr-korolev")
    assert row["ga"] == 8
    assert s["seasons"] == [
        {"slug": "2026", "label": "2026", "gf": 2, "ga": 3, "final_place": None}
    ]
    assert client.get("/stats", params={"season": "all"}).json()["season"] == "all"


def test_sitemap(client):
    paths = {item["path"] for item in client.get("/sitemap").json()}
    static = {
        "/",
        "/matches",
        "/team",
        "/hall-of-fame",
        "/news",
        "/standings",
        "/about",
        "/join",
        "/partners",
    }
    assert static <= paths
    assert "/history" not in paths  # постоянный редирект на /hall-of-fame
    assert "/matches/2026-09-06-bauman-junior" in paths
    assert "/team/aleksandr-korolev" in paths
    assert "/news/start" in paths


def test_sitemap_includes_undated_match(client, db):
    from .test_matches import add_undated

    add_undated(db)
    paths = {item["path"] for item in client.get("/sitemap").json()}
    assert "/matches/kvazar-5877228" in paths


def test_sitemap_lastmod_follows_data_not_today(client, db):
    from datetime import UTC, datetime

    from bu_core.models import Match
    from sqlalchemy import update

    db.execute(update(Match).values(updated_at=datetime(2026, 9, 7, 12, tzinfo=UTC)))
    db.commit()
    items = {item["path"]: item["lastmod"] for item in client.get("/sitemap").json()}
    assert items["/matches"] == "2026-09-07"
    assert items["/matches/2026-09-06-bauman-junior"] == "2026-09-07"
    # игрок, отметившийся в матче, — по последнему такому матчу
    assert any(v == "2026-09-07" for k, v in items.items() if k.startswith("/team/"))
    assert items["/news/start"] is not None
