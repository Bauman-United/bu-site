def test_stats_current_and_all(client):
    s = client.get("/stats").json()
    assert s["season"] == "2026-27"
    assert s["leaders"]["goals"][0]["slug"] == "aleksandr-korolev"
    row = next(p for p in s["players"] if p["slug"] == "aleksandr-korolev")
    assert row["ga"] == 8
    assert s["seasons"] == [
        {"slug": "2026-27", "label": "2026/27", "gf": 2, "ga": 3, "final_place": None}
    ]
    assert client.get("/stats", params={"season": "all"}).json()["season"] == "all"


def test_sitemap(client):
    paths = {item["path"] for item in client.get("/sitemap").json()}
    assert {"/", "/matches", "/team", "/news", "/standings", "/about", "/join"} <= paths
    assert "/matches/2026-09-06-bauman-junior" in paths
    assert "/team/aleksandr-korolev" in paths
    assert "/news/start" in paths
