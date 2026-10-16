"""Общее для публичных форм (/join, /partners): лимит по IP и отправка владельцу в Telegram."""

import logging
import threading
import time
from collections import defaultdict, deque

import httpx
from bu_core.settings import Settings
from fastapi import HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)
# httpx пишет в INFO полный URL запроса, а в URL Bot API лежит токен — глушим.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

RATE_LIMIT = 3
RATE_WINDOW_S = 3600.0
TIMEOUT_S = 10.0


class RateLimiter:
    """Не больше `limit` принятых заявок с одного IP за `window` секунд (в памяти процесса)."""

    def __init__(self, limit: int = RATE_LIMIT, window: float = RATE_WINDOW_S) -> None:
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        return hits

    def allowed(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) < self.limit

    def record(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    if first:
        return first
    return request.client.host if request.client else "unknown"


def _limiter(request: Request, form: str) -> RateLimiter:
    """Свой лимитер на каждую форму, живёт в app.state."""
    limiters: dict[str, RateLimiter] | None = getattr(request.app.state, "form_limiters", None)
    if limiters is None:
        limiters = request.app.state.form_limiters = {}
    return limiters.setdefault(form, RateLimiter())


def send_telegram(
    settings: Settings, chat_id: str, text: str, transport: httpx.BaseTransport | None
) -> None:
    """Bot API sendMessage. Ошибки — HTTPException 502; URL (с токеном) в логи не попадает."""
    url = f"{settings.telegram_api_base.rstrip('/')}/bot{settings.telegram_bot_token}/sendMessage"
    try:
        with httpx.Client(transport=transport, timeout=TIMEOUT_S) as client:
            res = client.post(url, json={"chat_id": chat_id, "text": text})
        ok = res.status_code == 200 and res.json().get("ok") is True
    except (httpx.HTTPError, ValueError) as e:
        log.error("telegram request failed (%s)", type(e).__name__)
        raise HTTPException(502, "telegram is unavailable") from None
    if not ok:
        log.error("telegram responded %s", res.status_code)
        raise HTTPException(502, "telegram is unavailable")


def deliver(request: Request, settings: Settings, form: str, text: str) -> None:
    """Проверки конфигурации и лимита, затем отправка (или лог в dry run) в личку владельца.

    Honeypot проверяет сам роут — до вызова, чтобы боты не тратили лимит.
    """
    chat_id = settings.join_chat_id or settings.telegram_chat_id
    if not settings.join_dry_run and not (settings.telegram_bot_token and chat_id):
        raise HTTPException(503, f"{form} is not configured")
    limiter, ip = _limiter(request, form), client_ip(request)
    if not limiter.allowed(ip):
        raise HTTPException(429, "too many requests")
    if settings.join_dry_run:
        log.warning("%s (dry run):\n%s", form, text)
    else:
        assert chat_id is not None
        transport = getattr(request.app.state, "telegram_transport", None)
        send_telegram(settings, chat_id, text, transport)
    limiter.record(ip)


FORM_RESPONSES: dict[int | str, dict[str, object]] = {429: {}, 502: {}, 503: {}}


class FormResult(BaseModel):
    ok: bool
