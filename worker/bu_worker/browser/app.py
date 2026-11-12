"""Браузерный воркер для страниц Join.Football за SafeLine (сервис `bu-browser`).

Порт fantasy-back (app/amateur/browser_worker.py). Chromium запускается как обычный
headed-браузер под Xvfb: без Playwright, CDP и remote-debugging. Маленькое MV3-расширение
забирает задание с loopback-эндпоинта, открывает URL в видимой вкладке и возвращает DOM.
Если SafeLine просит «Confirm You Are Human», человек жмёт кнопку через noVNC
(SSH-туннель), а cookie остаются в постоянном профиле.

Запуск: `uvicorn bu_worker.browser.app:app --port 8090` (см. deploy/browser.Dockerfile).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from bu_worker.waf import is_safeline_challenge, is_waf_host

log = logging.getLogger("bu_browser")

PROFILE_DIR = os.getenv("BROWSER_PROFILE_DIR", "/data/browser/profile")
EXTENSION_DIR = os.getenv("BROWSER_EXTENSION_DIR", str(Path(__file__).with_name("extension")))
CHALLENGE_TIMEOUT_S = float(os.getenv("BROWSER_CHALLENGE_TIMEOUT_SECONDS", "35"))
NAVIGATION_TIMEOUT_S = float(os.getenv("BROWSER_NAVIGATION_TIMEOUT_SECONDS", "45"))
RESULT_TIMEOUT_S = NAVIGATION_TIMEOUT_S + CHALLENGE_TIMEOUT_S


class FetchRequest(BaseModel):
    url: str


class FetchResponse(BaseModel):
    html: str
    final_url: str


class ExtensionResult(BaseModel):
    job_id: str
    html: str
    final_url: str


@dataclass
class BrowserJob:
    url: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event: asyncio.Event = field(default_factory=asyncio.Event)
    html: str | None = None
    final_url: str | None = None


class ChallengeAlerts:
    """Одно сообщение о заглушке и одно о восстановлении — в чат алертов bu-site."""

    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
        console_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token if token is not None else os.getenv("BU_TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id if chat_id is not None else os.getenv("BU_TELEGRAM_CHAT_ID", "")
        self._console_url = (
            console_url if console_url is not None else os.getenv("BU_BROWSER_NOVNC_URL", "")
        )
        self._transport = transport
        self.challenge_active = False

    async def _send(self, text: str, reply_markup: dict | None = None) -> bool:
        if not self._token or not self._chat_id:
            log.warning("alert (telegram not configured): %s", text)
            return False
        payload: dict = {"chat_id": self._chat_id, "text": f"⚠️ bu-site: {text}"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=15) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage", json=payload
                )
                response.raise_for_status()
        except httpx.HTTPError:
            log.exception("telegram alert failed")
            return False
        return True

    async def challenge(self, url: str) -> None:
        if self.challenge_active:
            return
        text = (
            "SafeLine остановил парсинг Бауманской лиги. Откройте браузерный воркер "
            "(noVNC) и нажмите Confirm You Are Human. Данные на сайте не перезаписываются.\n"
            f"Страница: {url}"
        )
        markup = None
        if self._console_url:
            markup = {"inline_keyboard": [[{"text": "Открыть браузер", "url": self._console_url}]]}
            text += "\nСсылка на 127.0.0.1 работает после SSH-туннеля: ssh -L 8436:127.0.0.1:8436"
        if await self._send(text, markup):
            self.challenge_active = True

    async def recovered(self, url: str) -> None:
        if not self.challenge_active:
            return
        if await self._send(f"SafeLine пройден, страницы БЛ снова загружаются ({url})."):
            self.challenge_active = False


def validate_url(url: str) -> None:
    parts = urlsplit(url)
    try:
        port = parts.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid URL port") from exc
    if parts.scheme != "https" or not is_waf_host(parts.hostname or ""):
        raise HTTPException(status_code=400, detail="only https Join.Football URLs are allowed")
    if parts.username or parts.password or port not in (None, 443):
        raise HTTPException(status_code=400, detail="credentials and custom ports are not allowed")


def _is_loopback(request: Request) -> bool:
    return request.client is not None and request.client.host in {"127.0.0.1", "::1"}


def _browser_executable() -> str:
    configured = os.getenv("BROWSER_EXECUTABLE", "").strip()
    if configured:
        return configured
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        if found := shutil.which(name):
            return found
    raise RuntimeError("Chromium executable was not found")


async def _launch_browser() -> asyncio.subprocess.Process:
    extension = Path(EXTENSION_DIR)
    if not (extension / "manifest.json").is_file():
        raise RuntimeError(f"browser extension is missing from {extension}")
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    process = await asyncio.create_subprocess_exec(
        _browser_executable(),
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate",
        "--lang=ru-RU",
        "--password-store=basic",
        f"--user-data-dir={PROFILE_DIR}",
        f"--disable-extensions-except={extension}",
        f"--load-extension={extension}",
        "--window-size=1365,900",
        "about:blank",
        stderr=asyncio.subprocess.STDOUT,
    )
    await asyncio.sleep(1)
    if process.returncode is not None:
        raise RuntimeError(f"Chromium exited during startup with code {process.returncode}")
    return process


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.browser_process = await _launch_browser()
    app.state.challenge_alerts = ChallengeAlerts()
    app.state.fetch_lock = asyncio.Lock()
    app.state.job = None
    app.state.challenge = False
    app.state.extension_seen_at = None
    try:
        yield
    finally:
        process: asyncio.subprocess.Process = app.state.browser_process
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


app = FastAPI(title="bu-browser", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, bool]:
    process: asyncio.subprocess.Process = app.state.browser_process
    if process.returncode is not None:
        raise HTTPException(status_code=503, detail="Chromium is not running")
    seen_at: float | None = app.state.extension_seen_at
    if seen_at is None or time.monotonic() - seen_at > 75:
        raise HTTPException(status_code=503, detail="browser extension is disconnected")
    return {"ok": True, "challenge": app.state.challenge}


@app.get("/extension/next")
async def extension_next(request: Request) -> dict:
    if not _is_loopback(request):
        raise HTTPException(status_code=403, detail="extension endpoint is loopback-only")
    app.state.extension_seen_at = time.monotonic()
    job: BrowserJob | None = app.state.job
    if job is None or job.event.is_set():
        return {"job": None}
    # Одно и то же задание отдаётся повторно намеренно: MV3 service worker может уснуть
    # между опросами, а chrome.storage помнит, что этот URL уже открыт.
    return {"job": {"id": job.id, "url": job.url}}


@app.post("/extension/result")
async def extension_result(payload: ExtensionResult, request: Request) -> dict[str, bool]:
    if not _is_loopback(request):
        raise HTTPException(status_code=403, detail="extension endpoint is loopback-only")
    app.state.extension_seen_at = time.monotonic()
    job: BrowserJob | None = app.state.job
    if job is None or payload.job_id != job.id or job.event.is_set():
        return {"complete": False}
    try:
        validate_url(payload.final_url)
    except HTTPException:
        return {"complete": False}

    if is_safeline_challenge(200, payload.html):
        app.state.challenge = True
        await app.state.challenge_alerts.challenge(job.url)
        return {"complete": False}
    # Страница ещё дорисовывается — ждём следующий снимок от расширения.
    if len(payload.html) < 1_000 or "<main" not in payload.html.lower():
        return {"complete": False}

    job.html = payload.html
    job.final_url = payload.final_url
    app.state.challenge = False
    job.event.set()
    await app.state.challenge_alerts.recovered(job.url)
    return {"complete": True}


@app.post("/fetch", response_model=FetchResponse)
async def fetch_page(payload: FetchRequest) -> FetchResponse:
    validate_url(payload.url)
    process: asyncio.subprocess.Process = app.state.browser_process
    if process.returncode is not None:
        raise HTTPException(status_code=503, detail="Chromium is not running")
    # Одна вкладка и одна навигация за раз: сессия браузера остаётся цельной.
    async with app.state.fetch_lock:
        job = BrowserJob(payload.url)
        app.state.job = job
        try:
            await asyncio.wait_for(job.event.wait(), timeout=RESULT_TIMEOUT_S)
        except TimeoutError as exc:
            detail = (
                "SafeLine challenge did not clear; open noVNC and confirm it"
                if app.state.challenge
                else "browser extension did not return a usable page"
            )
            raise HTTPException(status_code=502, detail=detail) from exc
        finally:
            app.state.job = None
        if job.html is None or job.final_url is None:
            raise HTTPException(status_code=502, detail="browser returned an empty result")
        return FetchResponse(html=job.html, final_url=job.final_url)
