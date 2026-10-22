"""IndexNow: сообщаем Яндексу об изменённых страницах, не дожидаясь обхода sitemap.

Яндекс передаёт адреса остальным поисковикам протокола (Bing и др.). Отправляем только
страницы, у которых изменился lastmod с прошлой успешной отправки: теги ревалидации
помечают и неизменённые записи, а лишние адреса поисковики считают спамом.
"""

import logging
from collections.abc import Iterable
from datetime import date

import httpx
from bu_core.models import Computed
from bu_core.settings import Settings
from bu_core.sitemap import sitemap_entries
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)
STATE_KEY = "indexnow"  # Computed: {путь: lastmod или ""} на момент последней отправки
BATCH = 10_000  # предел протокола на один запрос
KEY_PATH = "/indexnow.txt"  # ключ отдаёт сайт (web/src/app/indexnow.txt)


def changed_paths(
    entries: Iterable[tuple[str, date | None]], sent: dict[str, str]
) -> tuple[list[str], dict[str, str]]:
    """Новые, изменённые и удалённые страницы (удалённые — чтобы поисковик увидел 404)."""
    current = {path: lastmod.isoformat() if lastmod else "" for path, lastmod in entries}
    changed = [path for path, lastmod in current.items() if sent.get(path) != lastmod]
    removed = [path for path in sent if path not in current]
    return changed + removed, current


def submit_changes(
    session: Session, settings: Settings, transport: httpx.BaseTransport | None = None
) -> int:
    """Отправляет изменённые адреса; возвращает их число. Без ключа (dev, noindex) — ничего."""
    if not settings.indexnow_key:
        return 0
    state = session.get(Computed, STATE_KEY)
    paths, current = changed_paths(sitemap_entries(session), state.data if state else {})
    if not paths:
        return 0
    site = settings.site_url.rstrip("/")
    urls = [f"{site}{path}" for path in paths]
    try:
        with httpx.Client(transport=transport, timeout=20) as client:
            for start in range(0, len(urls), BATCH):
                response = client.post(
                    settings.indexnow_endpoint,
                    json={
                        "host": httpx.URL(site).host,
                        "key": settings.indexnow_key,
                        "keyLocation": f"{site}{KEY_PATH}",
                        "urlList": urls[start : start + BATCH],
                    },
                )
                response.raise_for_status()  # 200/202 — принято
    except httpx.HTTPError:
        # Состояние не сохраняем: в следующий запуск отправим те же адреса ещё раз.
        log.exception("indexnow failed")
        return 0
    if state is None:
        session.add(Computed(key=STATE_KEY, data=current))
    else:
        state.data = current
    session.commit()
    log.info("indexnow: %s urls", len(urls))
    return len(urls)
