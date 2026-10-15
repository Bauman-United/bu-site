def test_news_pagination_and_tag(client):
    page = client.get("/news", params={"per_page": 1}).json()
    assert page["total"] == 2 and page["items"][0]["slug"] == "club-news"
    tagged = client.get("/news", params={"tag": "match"}).json()
    assert [n["slug"] for n in tagged["items"]] == ["start"]


def test_news_detail(client):
    assert client.get("/news/start").json()["body_md"] == "Текст"
    assert client.get("/news/missing").status_code == 404
