import asyncio

import httpx
import pytest
from bu_core.settings import Settings
from bu_worker import waf
from bu_worker.browser import app as browser
from bu_worker.http import PoliteClient
from bu_worker.runner import make_client
from fastapi import HTTPException
from starlette.requests import Request

CHALLENGE = '<html><body><div id="slg-box">Confirm You Are Human</div></body></html>'
PAGE = "<html><main>" + "calendar " * 150 + "</main></html>"
BASE = "https://bauman_league.join.football"


def test_detects_safeline_challenge():
    assert waf.is_safeline_challenge(468, "")
    assert waf.is_safeline_challenge(200, CHALLENGE)
    assert waf.is_safeline_challenge(200, '<script src="/.safeline/static/x.js"></script>')
    assert not waf.is_safeline_challenge(200, PAGE)


def test_reader_url_only_for_join_football():
    assert (
        waf.reader_url(f"{BASE}/tournament/1/calendar?x=1")
        == "https://r.jina.ai/http://bauman_league.join.football/tournament/1/calendar?x=1"
    )
    with pytest.raises(ValueError):
        waf.reader_url("https://lfl.ru/club14270")


def test_chain_skips_failures_and_challenges():
    calls = []

    def broken(url):
        calls.append("broken")
        raise httpx.ConnectError("down")

    def blocked(url):
        calls.append("blocked")
        return CHALLENGE

    def good(url):
        calls.append("good")
        return PAGE

    fetch = waf.chain(("browser", broken), ("reader", blocked), ("last", good))
    assert fetch(f"{BASE}/x") == PAGE
    assert calls == ["broken", "blocked", "good"]
    with pytest.raises(waf.WafBlockedError):
        waf.chain(("reader", blocked))(f"{BASE}/x")


def test_browser_fetcher_posts_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content
        return httpx.Response(200, json={"html": PAGE, "final_url": f"{BASE}/x"})

    fetch = waf.browser_fetcher("http://bu-browser:8090/", httpx.MockTransport(handler))
    assert fetch(f"{BASE}/x") == PAGE
    assert seen["url"] == "http://bu-browser:8090/fetch"
    assert b"bauman_league.join.football/x" in seen["body"]


def test_reader_fetcher_rejects_challenge():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-return-format"] == "html"
        return httpx.Response(200, text=CHALLENGE)

    with pytest.raises(waf.WafBlockedError):
        waf.reader_fetcher(httpx.MockTransport(handler))(f"{BASE}/x")


def _client(handler, fallback):
    return PoliteClient(
        BASE,
        "BaumanUnitedBot/1.0",
        0,
        transport=httpx.MockTransport(handler),
        waf_fallback=fallback,
    )


def test_polite_client_falls_back_on_safeline_and_stays_on_fallback():
    direct, fallen = [], []

    def handler(request: httpx.Request) -> httpx.Response:
        direct.append(request.url.path)
        return httpx.Response(468, text=CHALLENGE)

    def fallback(url):
        fallen.append(url)
        return PAGE

    client = _client(handler, fallback)
    assert client.get("/tournament/1/calendar") == PAGE
    assert client.get("/tournament/1/tables") == PAGE
    # robots.txt уже вернул заглушку — дальше напрямую не ходим
    assert direct == ["/robots.txt"]
    assert fallen == [f"{BASE}/tournament/1/calendar", f"{BASE}/tournament/1/tables"]


def test_polite_client_falls_back_on_403_page():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(403, text="")

    assert _client(handler, lambda url: PAGE).get("/tournament/1/calendar") == PAGE


def test_polite_client_without_fallback_raises_as_before():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="")

    with pytest.raises(httpx.HTTPStatusError):
        _client(handler, None).get("/tournament/1/calendar")


def test_make_client_enables_fallback_only_for_join_football():
    settings = Settings(browser_worker_url="http://bu-browser:8090")
    assert make_client(settings, "joinfootball")._waf_fallback is not None
    assert make_client(settings, "lfl")._waf_fallback is None
    assert make_client(settings, "ifl")._waf_fallback is None
    off = Settings(browser_worker_url=None, waf_reader_fallback=False)
    assert make_client(off, "joinfootball")._waf_fallback is None


class _Alerts:
    def __init__(self):
        self.challenges, self.recoveries = [], []

    async def challenge(self, url):
        self.challenges.append(url)

    async def recovered(self, url):
        self.recoveries.append(url)


def _request(host="127.0.0.1"):
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/extension/result",
            "headers": [],
            "client": (host, 12345),
            "server": ("127.0.0.1", 8090),
            "scheme": "http",
            "query_string": b"",
        }
    )


def _arm(challenge=False):
    alerts = _Alerts()
    job = browser.BrowserJob(f"{BASE}/tournament/1/calendar")
    browser.app.state.job = job
    browser.app.state.challenge = challenge
    browser.app.state.challenge_alerts = alerts
    return job, alerts


def test_extension_challenge_keeps_job_pending():
    job, alerts = _arm()
    result = asyncio.run(
        browser.extension_result(
            browser.ExtensionResult(job_id=job.id, html=CHALLENGE, final_url=job.url), _request()
        )
    )
    assert result == {"complete": False}
    assert browser.app.state.challenge is True
    assert not job.event.is_set()
    assert alerts.challenges == [job.url]


def test_extension_accepts_real_page():
    job, alerts = _arm(challenge=True)
    result = asyncio.run(
        browser.extension_result(
            browser.ExtensionResult(job_id=job.id, html=PAGE, final_url=job.url), _request()
        )
    )
    assert result == {"complete": True}
    assert job.html == PAGE and job.event.is_set()
    assert browser.app.state.challenge is False
    assert alerts.recoveries == [job.url]


def test_extension_bridge_is_loopback_only():
    job, _ = _arm()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            browser.extension_result(
                browser.ExtensionResult(job_id=job.id, html=PAGE, final_url=job.url),
                _request("172.20.0.10"),
            )
        )
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "http://bauman_league.join.football/x",
        "https://lfl.ru/x",
        "https://user:pw@bauman_league.join.football/x",
        "https://bauman_league.join.football:8443/x",
    ],
)
def test_fetch_rejects_foreign_urls(url):
    with pytest.raises(HTTPException) as exc:
        browser.validate_url(url)
    assert exc.value.status_code == 400


def test_challenge_alert_sent_once_with_console_button():
    sent = []

    async def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.content)
        return httpx.Response(200, json={"ok": True})

    alerts = browser.ChallengeAlerts(
        "token", "42", "http://127.0.0.1:8436/vnc.html", httpx.MockTransport(handler)
    )

    async def scenario():
        await alerts.challenge(f"{BASE}/a")
        await alerts.challenge(f"{BASE}/b")
        await alerts.recovered(f"{BASE}/b")

    asyncio.run(scenario())
    assert len(sent) == 2
    assert b"inline_keyboard" in sent[0] and b"vnc.html" in sent[0]
    assert alerts.challenge_active is False
