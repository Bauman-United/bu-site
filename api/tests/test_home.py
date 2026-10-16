from bu_core.models import Match
from sqlalchemy import select

from .test_matches import add_undated


def test_home_aggregate(client):
    home = client.get("/home").json()
    assert home["next_match"]["slug"] == "2026-10-25-messiya"
    assert home["last_match"]["slug"] == "2026-09-06-bauman-junior"
    assert home["last_match"]["scorers_us"] == ["Королев 22'"]
    assert [f["outcome"] for f in home["form"]] == ["L"]
    assert home["standings"]["rows"][-1]["is_us"] is True
    assert len(home["news"]) == 2
    assert home["leaders"]["goals"]["slug"] == "aleksandr-korolev"
    assert home["leaders"]["assists"]["value"] == 6
    assert home["numbers"]["founded"] == 2019
    assert home["live"] is None


def test_home_prefers_dated_upcoming_over_undated(client, db):
    add_undated(db)
    assert client.get("/home").json()["next_match"]["slug"] == "2026-10-25-messiya"


def test_home_falls_back_to_undated_upcoming(client, db):
    add_undated(db)
    dated = db.scalars(select(Match).where(Match.slug == "2026-10-25-messiya")).one()
    dated.status = "cancelled"
    db.flush()
    nxt = client.get("/home").json()["next_match"]
    assert nxt["slug"] == "kvazar-5877228" and nxt["kickoff"] is None
