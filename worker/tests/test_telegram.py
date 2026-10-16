from datetime import UTC, datetime
from pathlib import Path

from bu_core.models import News
from bu_worker.pipeline.telegram import ingest, to_news
from bu_worker.sources.telegram import TgPost, parse_channel_page
from sqlalchemy import select

FIX = Path(__file__).parent / "fixtures" / "telegram" / "channel.html"


def page():
    return parse_channel_page(FIX.read_text(encoding="utf-8"), "baumanunited")


def by_id(posts, post_id):
    return next(p for p in posts if p.id == post_id)


def test_parse_channel_page():
    posts, before = page()
    assert len(posts) == 16
    assert before == 994
    lineup = by_id(posts, 995)
    assert lineup.date == datetime(2026, 10, 11, 18, 4, 34, tzinfo=UTC)
    assert lineup.text.startswith("Наш состав на игру с Реактором!")
    assert lineup.photo and lineup.photo.startswith("https://cdn")
    assert lineup.url == "https://t.me/baumanunited/995"
    stream = by_id(posts, 996)
    assert "[https://vkvideo.ru/" in stream.markdown or "https://vkvideo.ru/" in stream.markdown


def test_only_real_posts_become_news():
    posts, _ = page()
    kept = sorted(p.id for p in posts if to_news(p) is not None)
    assert kept == [995, 1003, 1004, 1005, 1006, 1007, 1013]


def test_news_fields_and_tags():
    posts, _ = page()
    transfer = to_news(by_id(posts, 1007))
    assert transfer is not None
    assert transfer.tag == "transfer"
    assert transfer.title == "Сообщим вам об еще одном нашем подписании"
    assert transfer.slug == "tg-1007"
    assert transfer.source_url == "https://t.me/baumanunited/1007"
    assert transfer.cover and transfer.cover.startswith("https://cdn")
    assert to_news(by_id(posts, 1013)).tag == "match"
    assert to_news(by_id(posts, 1003)).tag == "club"
    assert len(to_news(by_id(posts, 1005)).title) <= 90


def test_ingest_upserts_and_survives_content_sync(db):
    from bu_worker.pipeline.content import sync_content
    from bu_worker.sources.content import ContentBundle

    posts, _ = page()
    result = ingest(db, posts)
    assert result.counts == {"posts": 16, "news": 7}
    assert "news" in result.tags and "news:tg-1007" in result.tags
    original = by_id(posts, 1007)
    edited = original.model_copy(
        update={
            "text": original.text + " Обновлено.",
            "markdown": original.markdown + " Обновлено.",
        }
    )
    ingest(db, [edited])
    news = db.scalars(select(News).where(News.slug == "tg-1007")).one()
    assert news.body_md.endswith("Обновлено.")
    assert news.origin == "telegram" and news.source_platform == "telegram"

    sync_content(
        db,
        ContentBundle(
            club={"name": "Бауман Юнайтед"},
            history={},
            tournaments=[],
            players={},
            news=[],
            matches={},
        ),
    )
    assert db.scalar(select(News).where(News.slug == "tg-1007")) is not None


def test_short_score_update_is_dropped():
    post = TgPost(
        id=1,
        url="https://t.me/x/1",
        date=datetime(2026, 10, 1, tzinfo=UTC),
        text="Королев сокращает разрыв! " * 3 + "Счёт теперь 3-4!",
        markdown="",
        photo=None,
    )
    assert to_news(post) is None


def test_fetch_pages_back_until_since_or_known():
    from datetime import date

    import httpx
    from bu_worker.http import PoliteClient
    from bu_worker.sources.telegram import fetch_posts

    first = FIX.read_text(encoding="utf-8")
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        requested.append(
            str(request.url.query, "utf-8")
            if isinstance(request.url.query, bytes)
            else str(request.url.query)
        )
        if "before=994" in requested[-1]:
            return httpx.Response(200, text="<html></html>")  # дальше постов нет
        return httpx.Response(200, text=first)

    client = PoliteClient(
        "https://t.me", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )
    posts = fetch_posts(
        client,
        "baumanunited",
        since=date(2026, 7, 1),
        known_max_id=None,
        max_pages=5,
        snapshot=lambda name, html: None,
    )
    assert len(posts) == 16 and len(requested) == 2

    requested.clear()
    fetch_posts(
        client,
        "baumanunited",
        since=date(2026, 7, 1),
        known_max_id=1000,
        max_pages=5,
        snapshot=lambda name, html: None,
    )
    assert len(requested) == 1  # страница уже содержит известные посты — дальше не листаем

    requested.clear()
    recent = fetch_posts(
        client,
        "baumanunited",
        since=date(2026, 10, 13),
        known_max_id=None,
        max_pages=5,
        snapshot=lambda name, html: None,
    )
    assert len(requested) == 1 and min(p.date.date() for p in recent) >= date(2026, 10, 13)
