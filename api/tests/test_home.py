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
