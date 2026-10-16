from bu_core.models import Match
from sqlalchemy import select

from .seed import seed_lfl
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
    assert [b["league"] for b in home["by_league"]] == ["bl"]
    bauman = home["by_league"][0]
    assert bauman["title"] == "Бауманская лига"
    assert bauman["last_match"]["slug"] == "2026-09-06-bauman-junior"
    assert bauman["standings"]["tournament"]["slug"] == "liga-inzhenerov"
    assert bauman["standings"]["rows"][-1]["is_us"] is True


def test_home_by_league_includes_lfl(client, db):
    from bu_core.models import Season

    season = db.scalars(select(Season)).one()
    seed_lfl(db, {"season": season})
    home = client.get("/home").json()
    leagues = {b["league"]: b for b in home["by_league"]}
    assert [b["league"] for b in home["by_league"]] == ["bl", "lfl"]
    assert leagues["bl"]["last_match"]["slug"] == "2026-09-06-bauman-junior"
    assert leagues["bl"]["standings"]["tournament"]["slug"] == "liga-inzhenerov"
    lfl = leagues["lfl"]
    assert lfl["title"] == "ЛФЛ"
    assert lfl["last_match"]["slug"] == "2026-08-30-politekh"
    assert lfl["last_match"]["tournament"]["short"] == "ЛФЛ"
    rows = lfl["standings"]["rows"]
    assert lfl["standings"]["tournament"]["slug"] == "lfl-8x8-2026-27"
    assert [r["pos"] for r in rows] == [3, 4, 5, 6, 7]
    assert rows[2]["is_us"] is True
    # старые поля на месте
    assert home["last_match"]["slug"] == "2026-09-06-bauman-junior"


def test_home_by_league_omits_empty_leagues(client, db):
    from bu_core.models import StandingRow

    for m in db.scalars(select(Match)):
        db.delete(m)
    for r in db.scalars(select(StandingRow)):
        db.delete(r)
    db.flush()
    assert client.get("/home").json()["by_league"] == []


def test_home_by_league_without_standings_keeps_last_match(client, db):
    from bu_core.models import StandingRow

    for r in db.scalars(select(StandingRow)):
        db.delete(r)
    db.flush()
    (bauman,) = client.get("/home").json()["by_league"]
    assert bauman["standings"] is None
    assert bauman["last_match"]["slug"] == "2026-09-06-bauman-junior"


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
