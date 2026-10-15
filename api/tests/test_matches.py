def test_list_and_filters(client):
    all_matches = client.get("/matches").json()
    assert [m["slug"] for m in all_matches] == ["2026-09-06-bauman-junior", "2026-10-25-messiya"]
    assert all_matches[0]["outcome"] == "L"
    assert all_matches[1]["outcome"] is None
    away = client.get("/matches", params={"where": "away"}).json()
    assert [m["slug"] for m in away] == ["2026-10-25-messiya"]
    finished = client.get("/matches", params={"status": "finished"}).json()
    assert len(finished) == 1


def test_detail(client):
    m = client.get("/matches/2026-09-06-bauman-junior").json()
    assert m["scorers_us"] == ["Королев 22'"]
    assert m["scorers_them"] == ["Горевой 19'"]
    us_goal = next(e for e in m["events"] if e["team"] == "us")
    assert us_goal["player_slug"] == "aleksandr-korolev"
    assert us_goal["player_name"] == "Александр Королев"
    assert m["report"]["slug"] == "start"
    assert m["prev_slug"] is None and m["next_slug"] == "2026-10-25-messiya"


def test_detail_404(client):
    assert client.get("/matches/nope").status_code == 404
