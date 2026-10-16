"""POST /join — заявка «Хочу в команду» → личное сообщение владельцу от бота клуба."""

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Annotated, Literal

import httpx
from bu_core.settings import Settings, get_settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

log = logging.getLogger(__name__)
# httpx пишет в INFO полный URL запроса, а в URL Bot API лежит токен — глушим.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

router = APIRouter()

RATE_LIMIT = 3
RATE_WINDOW_S = 3600.0
TIMEOUT_S = 10.0


class JoinRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    position: Literal["Вратарь", "Защитник", "Полузащитник", "Нападающий", "Пока не знаю"]
    experience: str = Field(min_length=10, max_length=1500)
    bauman: Literal["Да, учусь", "Выпускник", "Нет"]
    age: int = Field(ge=14, le=70)
    contact: str = Field(min_length=3, max_length=200)
    website: str = Field(default="", max_length=500)  # honeypot: люди его не видят


class JoinResult(BaseModel):
    ok: bool


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


def format_message(form: JoinRequest) -> str:
    return (
        "⚽ Новая заявка в команду\n"
        f"Имя: {form.name}\n"
        f"Позиция: {form.position}\n"
        f"Возраст: {form.age}\n"
        f"Бауманка: {form.bauman}\n"
        f"Контакт: {form.contact}\n"
        f"Опыт:\n{form.experience}"
    )


def _limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter | None = getattr(request.app.state, "join_limiter", None)
    if limiter is None:
        limiter = request.app.state.join_limiter = RateLimiter()
    return limiter


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
        log.error("join: telegram request failed (%s)", type(e).__name__)
        raise HTTPException(502, "telegram is unavailable") from None
    if not ok:
        log.error("join: telegram responded %s", res.status_code)
        raise HTTPException(502, "telegram is unavailable")


@router.post("/join", responses={429: {}, 502: {}, 503: {}})
def join(
    form: JoinRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JoinResult:
    if form.website:
        log.info("join: honeypot filled, dropped")
        return JoinResult(ok=True)
    chat_id = settings.join_chat_id or settings.telegram_chat_id
    if not settings.join_dry_run and not (settings.telegram_bot_token and chat_id):
        raise HTTPException(503, "join is not configured")
    limiter, ip = _limiter(request), client_ip(request)
    if not limiter.allowed(ip):
        raise HTTPException(429, "too many requests")
    text = format_message(form)
    if settings.join_dry_run:
        log.warning("join (dry run):\n%s", text)
    else:
        assert chat_id is not None
        transport = getattr(request.app.state, "telegram_transport", None)
        send_telegram(settings, chat_id, text, transport)
    limiter.record(ip)
    return JoinResult(ok=True)
