import httpx
import pytest
from bu_worker.http import DisallowedError, PoliteClient

ROBOTS = "User-agent: *\nDisallow: /matches\nDisallow: /player\n"


def make(handler):
    return PoliteClient(
        "https://jf.test", "BaumanUnitedBot/1.0", delay_s=0, transport=httpx.MockTransport(handler)
    )


def test_respects_robots_and_sets_user_agent():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.headers["user-agent"], request.headers["accept"]))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        return httpx.Response(200, text="<html>ok</html>")

    client = make(handler)
    assert client.get("/match/1") == "<html>ok</html>"
    with pytest.raises(DisallowedError):
        client.get("/player/5")
    assert any(
        path == "/match/1" and agent == "BaumanUnitedBot/1.0" and "text/html" in accept
        for path, agent, accept in seen
    )
    assert all(path != "/player/5" for path, _, _ in seen)


def test_retries_server_errors():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(502) if calls["n"] < 3 else httpx.Response(200, text="ok")

    assert make(handler).get("/tournament/1") == "ok"
    assert calls["n"] == 3


def test_post_sends_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        seen["method"] = request.method
        seen["body"] = request.content
        return httpx.Response(200, text='{"ok":true}')

    assert make(handler).post("/stats", {"season_id": 15}) == '{"ok":true}'
    assert seen == {"method": "POST", "body": b'{"season_id":15}'}


def test_underscore_host_uses_hyphen_sni():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions.get("sni_hostname"))
        return httpx.Response(200, text="ok")

    client = PoliteClient(
        "https://bauman_league.join.football",
        "BaumanUnitedBot/1.0",
        0,
        transport=httpx.MockTransport(handler),
    )
    client.get("/tournament/1")
    assert seen and all(s == "bauman-league.join.football" for s in seen)
