from bu_core.models import Match, Tournament
from sqlalchemy import select


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


def test_kickoff_is_in_moscow_time(client):
    m = client.get("/matches").json()[0]
    assert m["kickoff"] == "2026-09-06T20:30:00+03:00"


def add_undated(db, slug: str = "kvazar-5877228") -> Match:
    t = db.scalars(select(Tournament)).first()
    m = Match(
        slug=slug,
        tournament_id=t.id,
        season_id=t.season_id,
        round="Четвертьфинал",
        kickoff=None,
        home=False,
        opponent_name="Квазар",
        status="scheduled",
        source="joinfootball",
        external_id="5877228",
    )
    db.add(m)
    db.flush()
    return m


def test_undated_match_is_listed_last(client, db):
    add_undated(db)
    matches = client.get("/matches").json()
    assert [m["slug"] for m in matches][-1] == "kvazar-5877228"
    assert matches[-1]["kickoff"] is None


def test_undated_match_detail(client, db):
    add_undated(db)
    m = client.get("/matches/kvazar-5877228").json()
    assert m["kickoff"] is None
    assert m["prev_slug"] == "2026-10-25-messiya" and m["next_slug"] is None
    assert client.get("/matches/2026-10-25-messiya").json()["next_slug"] == "kvazar-5877228"
