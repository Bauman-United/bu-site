from datetime import date

import httpx
from bu_core.models import News
from bu_worker.pipeline.media import localize_news_media, make_downloader

JPEG = b"\xff\xd8\xff fake jpeg"


def tg_news(db, slug: str, cover: str | None, video: str | None = None) -> News:
    n = News(
        slug=slug,
        date=date(2026, 10, 1),
        tag="club",
        title="t",
        body_md="",
        cover=cover,
        cover_video=video,
        origin="telegram",
    )
    db.add(n)
    db.flush()
    return n


def downloader(calls: list[str], status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        kind = "video/mp4" if request.url.path.endswith(".mp4") else "image/jpeg"
        return httpx.Response(status, content=JPEG, headers={"content-type": kind})

    return make_downloader("test", transport=httpx.MockTransport(handler))


def test_downloads_once_and_rewrites_to_own_path(db, tmp_path):
    news = tg_news(
        db, "tg-1", "https://cdn4.telesco.pe/file/a.jpg", "https://cdn4.telesco.pe/file/v.mp4"
    )
    calls: list[str] = []
    tags = localize_news_media(db, tmp_path, downloader(calls))
    assert news.cover == "/media/tg/tg-1.jpg"
    assert news.cover_video == "/media/tg/tg-1-video.mp4"
    assert (tmp_path / "tg" / "tg-1.jpg").read_bytes() == JPEG
    assert tags == {"news:tg-1"}
    assert len(calls) == 2

    # ежедневный перескан вернул новую временную ссылку — файл уже есть, не качаем
    news.cover = "https://cdn4.telesco.pe/file/b.jpg"
    calls.clear()
    localize_news_media(db, tmp_path, downloader(calls))
    assert news.cover == "/media/tg/tg-1.jpg"
    assert calls == []


def test_failed_download_keeps_external_url(db, tmp_path):
    news = tg_news(db, "tg-2", "https://cdn4.telesco.pe/file/x.jpg")
    calls: list[str] = []
    assert localize_news_media(db, tmp_path, downloader(calls, status=404)) == set()
    assert news.cover == "https://cdn4.telesco.pe/file/x.jpg"
    assert not list((tmp_path / "tg").iterdir())


def test_content_news_untouched(db, tmp_path):
    n = News(
        slug="c", date=date(2026, 10, 1), tag="club", title="t", body_md="", cover="https://x/y.jpg"
    )
    db.add(n)
    db.flush()
    calls: list[str] = []
    localize_news_media(db, tmp_path, downloader(calls))
    assert n.cover == "https://x/y.jpg" and calls == []
