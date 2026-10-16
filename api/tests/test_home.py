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
    assert lfl["standings"]["tournament"]["slug"] == "lfl-8x8-2026"
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


def test_home_leaders_have_photo_and_number(client, db):
    from bu_core.models import Player
    from bu_core.recompute import recompute

    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    korolev.photo = "https://lfl.ru/korolev.jpg"
    db.flush()
    recompute(db)
    goals = client.get("/home").json()["leaders"]["goals"]
    assert (goals["photo"], goals["number"]) == ("https://lfl.ru/korolev.jpg", 10)


def test_home_leaders_photo_is_current_even_if_computed_doc_is_stale(client, db):
    """Computed-документ, посчитанный до появления photo в лидерах, — фото берётся из Player."""
    from bu_core.models import Computed, Player

    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    korolev.photo = "https://lfl.ru/new.jpg"
    for doc in db.scalars(select(Computed).where(Computed.key.like("season:%"))):
        doc.data = {
            **doc.data,
            "leaders": {
                k: [{kk: vv for kk, vv in x.items() if kk not in ("photo", "number")} for x in v]
                for k, v in doc.data["leaders"].items()
            },
        }
    db.flush()
    goals = client.get("/home").json()["leaders"]["goals"]
    assert (goals["photo"], goals["number"]) == ("https://lfl.ru/new.jpg", 10)
