"""Страницы Join.Football за SafeLine WAF: распознавание заглушки и фолбэки загрузки.

Порт решения из fantasy-back (app/amateur/joinfootball_http.py): сначала обычный HTTP,
на заглушке SafeLine — внутренний браузерный воркер (`bu-browser`), последним — Jina Reader.
"""

import logging
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit

import httpx

log = logging.getLogger(__name__)

BLOCK_STATUSES = (403, 429, 468)
READER_BASE_URL = "https://r.jina.ai/http://"
READER_HEADERS = {
    "X-Return-Format": "html",
    # Свежий запрос Reader может получить ту же заглушку; его недавний снимок из браузера
    # всё равно годится, а сам источник мы каждый раз пробуем первым.
    "X-Cache-Tolerance": "3600",
}
READER_TIMEOUT_S = 45.0
BROWSER_TIMEOUT_S = 90.0


class WafBlockedError(RuntimeError):
    """SafeLine не пустил ни напрямую, ни через фолбэки."""


def is_waf_host(host: str) -> bool:
    return host.lower().endswith(".join.football")


def is_safeline_challenge(status_code: int, text: str) -> bool:
    """Ответ — заглушка SafeLine (468 или её вёрстка), а не страница лиги."""
    if status_code == 468:
        return True
    body = text[:50_000]
    # Через Reader заглушка приходит без скриптов: маркеров SafeLineChallenge нет,
    # остаётся вёрстка (#slg-box). Парсер принял бы её за протокол без составов.
    return (
        "SafeLineChallenge" in body
        or "/.safeline/" in body
        or "slg-box" in body
        or "Debugging Detected" in body
    )


def reader_url(url: str) -> str:
    parts = urlsplit(url)
    if not is_waf_host(parts.hostname or ""):
        raise ValueError("Reader fallback is restricted to Join.Football hosts")
    # http://-форма источника: Reader не спотыкается о wildcard-сертификат с «_» в имени.
    source = urlunsplit(("http", parts.netloc, parts.path, parts.query, ""))
    return READER_BASE_URL + source.removeprefix("http://")


Fetcher = Callable[[str], str]


def browser_fetcher(endpoint: str, transport: httpx.BaseTransport | None = None) -> Fetcher:
    """Загрузка через `bu-browser`: POST {url} → {html}."""
    url = endpoint.rstrip("/") + "/fetch"

    def fetch(page_url: str) -> str:
        with httpx.Client(transport=transport) as client:
            response = client.post(
                url,
                json={"url": page_url},
                timeout=httpx.Timeout(BROWSER_TIMEOUT_S, connect=2.0),
            )
        response.raise_for_status()
        html = response.json().get("html")
        if not isinstance(html, str) or not html:
            raise WafBlockedError("browser worker returned an empty page")
        return html

    return fetch


def reader_fetcher(transport: httpx.BaseTransport | None = None) -> Fetcher:
    def fetch(page_url: str) -> str:
        with httpx.Client(transport=transport, follow_redirects=True) as client:
            response = client.get(
                reader_url(page_url), headers=READER_HEADERS, timeout=READER_TIMEOUT_S
            )
        if is_safeline_challenge(response.status_code, response.text):
            raise WafBlockedError("Reader тоже получил заглушку SafeLine")
        response.raise_for_status()
        return response.text

    return fetch


def chain(*fetchers: tuple[str, Fetcher]) -> Fetcher:
    """Пробует фолбэки по очереди; заглушка SafeLine в ответе — тоже провал."""

    def fetch(page_url: str) -> str:
        errors: list[str] = []
        for name, fetcher in fetchers:
            try:
                html = fetcher(page_url)
            except (httpx.HTTPError, ValueError, WafBlockedError) as exc:
                log.warning("SafeLine fallback %s failed for %s: %r", name, page_url, exc)
                errors.append(f"{name}: {exc}")
                continue
            if is_safeline_challenge(200, html):
                errors.append(f"{name}: заглушка SafeLine")
                continue
            log.info("SafeLine: %s загружена через %s", page_url, name)
            return html
        raise WafBlockedError(f"SafeLine на {page_url}; " + "; ".join(errors or ["нет фолбэков"]))

    return fetch
