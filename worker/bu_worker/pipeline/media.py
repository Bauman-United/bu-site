"""Свои копии обложек новостей из Telegram.

Ссылки CDN Telegram (cdn*.telesco.pe) временные: канал перечитываем раз в день и получаем
новые, но адрес картинки всё равно меняется каждый день — превью в соцсетях и картинки
в поисковиках со временем отваливаются. Поэтому файл скачиваем один раз и отдаём с сайта
(/media/…). Пост, у которого в Telegram заменили фото, сохраняет старую обложку.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import httpx
from bu_core.models import News
from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)
URL_PREFIX = "/media/tg"
MAX_BYTES = 30 * 1024 * 1024  # гифки из Telegram — mp4 в несколько мегабайт
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "video/mp4": ".mp4"}
FIELDS = {"cover": "", "cover_video": "-video"}

Download = Callable[[str], tuple[bytes, str]]  # url -> (содержимое, расширение)


def make_downloader(user_agent: str, transport: httpx.BaseTransport | None = None) -> Download:
    client = httpx.Client(
        headers={"User-Agent": user_agent}, timeout=30, follow_redirects=True, transport=transport
    )

    def download(url: str) -> tuple[bytes, str]:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            kind = response.headers.get("content-type", "").split(";")[0].strip()
            ext = EXT.get(kind) or Path(httpx.URL(url).path).suffix.lower()
            if ext not in EXT.values():
                raise ValueError(f"unexpected media type {kind!r}")
            data = b""
            for chunk in response.iter_bytes():
                data += chunk
                if len(data) > MAX_BYTES:
                    raise ValueError("media too large")
        return data, ext

    return download


def _existing(folder: Path, stem: str) -> Path | None:
    return next((p for p in sorted(folder.glob(f"{stem}.*")) if p.suffix in EXT.values()), None)


def localize_news_media(session: Session, media_dir: Path, download: Download) -> set[str]:
    """Меняет внешние обложки telegram-новостей на свои копии; возвращает теги изменённых."""
    folder = media_dir / "tg"
    folder.mkdir(parents=True, exist_ok=True)
    tags: set[str] = set()
    for news in session.scalars(select(News).where(News.origin == "telegram")):
        for field, suffix in FIELDS.items():
            url = getattr(news, field)
            if not url or not url.startswith(("http://", "https://")):
                continue
            stem = f"{news.slug}{suffix}"
            path = _existing(folder, stem)
            if path is None:
                try:
                    data, ext = download(url)
                except (httpx.HTTPError, ValueError) as exc:
                    log.warning("media %s: %s", news.slug, exc)  # остаётся внешняя ссылка
                    continue
                path = folder / f"{stem}{ext}"
                tmp = path.with_suffix(f"{ext}.part")
                tmp.write_bytes(data)
                tmp.replace(path)
            setattr(news, field, f"{URL_PREFIX}/{path.name}")
            tags.add(f"news:{news.slug}")
    session.flush()
    return tags
