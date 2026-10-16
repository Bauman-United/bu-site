def test_news_pagination_and_tag(client):
    page = client.get("/news", params={"per_page": 1}).json()
    assert page["total"] == 2 and page["items"][0]["slug"] == "club-news"
    tagged = client.get("/news", params={"tag": "match"}).json()
    assert [n["slug"] for n in tagged["items"]] == ["start"]


def test_news_detail(client):
    assert client.get("/news/start").json()["body_md"] == "Текст"
    assert client.get("/news/missing").status_code == 404


def test_news_detail_exposes_gif_video(client, db):
    from bu_core.models import News
    from sqlalchemy import select

    n = db.scalars(select(News).where(News.slug == "start")).one()
    n.cover, n.cover_video = "https://cdn4.telesco.pe/thumb.jpg", "https://cdn4.telesco.pe/a.mp4"
    db.flush()
    detail = client.get("/news/start").json()
    assert detail["cover_video"] == "https://cdn4.telesco.pe/a.mp4"
    assert detail["cover"] == "https://cdn4.telesco.pe/thumb.jpg"
