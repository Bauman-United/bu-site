import json
import logging

import httpx
import pytest
from bu_api.app import create_app
from bu_core.settings import Settings, get_settings
from fastapi.testclient import TestClient

TOKEN = "123:SECRET-TOKEN"

FORM = {
    "name": "Иван Иванов",
    "position": "Защитник",
    "experience": "Секция ЦСКА 5 лет, любительская лига",
    "bauman": "Да, учусь",
    "age": 21,
    "contact": "@ivan",
    "website": "",
}


def make_client(
    settings: Settings, handler=None, calls: list[httpx.Request] | None = None
) -> TestClient:
    app = create_app(lambda: None)  # type: ignore[arg-type, return-value]
    app.dependency_overrides[get_settings] = lambda: settings
    sent = calls if calls is not None else []

    def default(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"ok": True, "result": {}})

    app.state.telegram_transport = httpx.MockTransport(handler or default)
    return TestClient(app)


def configured(**kw) -> Settings:
    base = {
        "telegram_bot_token": TOKEN,
        "telegram_chat_id": "-100500",
        "join_chat_id": "42",
        "telegram_api_base": "https://tg.test",
    }
    return Settings(**{**base, **kw})


def test_join_sends_one_message_with_all_fields(caplog):
    caplog.set_level(logging.DEBUG)
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    res = client.post("/join", json=FORM)
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert len(calls) == 1
    req = calls[0]
    assert str(req.url) == f"https://tg.test/bot{TOKEN}/sendMessage"
    body = json.loads(req.content)
    assert body["chat_id"] == "42"
    text = body["text"]
    assert text.startswith("⚽ Новая заявка в команду")
    for value in ("Иван Иванов", "Защитник", "21", "Да, учусь", "@ivan", "Секция ЦСКА 5 лет"):
        assert value in text
    assert TOKEN not in caplog.text


def test_join_falls_back_to_telegram_chat_id():
    calls: list[httpx.Request] = []
    client = make_client(configured(join_chat_id=None), calls=calls)
    assert client.post("/join", json=FORM).status_code == 200
    assert json.loads(calls[0].content)["chat_id"] == "-100500"


def test_join_honeypot_not_sent():
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    res = client.post("/join", json={**FORM, "website": "http://spam.example"})
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "И"),
        ("position", "Тренер"),
        ("experience", "мало"),
        ("bauman", "Может быть"),
        ("age", 13),
        ("age", 71),
        ("contact", "ab"),
    ],
)
def test_join_invalid_data_422(field, value):
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    res = client.post("/join", json={**FORM, field: value})
    assert res.status_code == 422
    assert any(err["loc"][-1] == field for err in res.json()["detail"])
    assert calls == []


def test_join_missing_field_422():
    client = make_client(configured())
    payload = {k: v for k, v in FORM.items() if k != "contact"}
    res = client.post("/join", json=payload)
    assert res.status_code == 422


def test_join_not_configured_503():
    client = make_client(
        Settings(
            telegram_bot_token=None, telegram_chat_id=None, join_chat_id=None, join_dry_run=False
        )
    )
    res = client.post("/join", json=FORM)
    assert res.status_code == 503
    assert res.json() == {"detail": "join is not configured"}


def test_join_dry_run_does_not_send(caplog):
    caplog.set_level(logging.INFO)
    calls: list[httpx.Request] = []
    settings = Settings(telegram_bot_token=None, telegram_chat_id=None, join_dry_run=True)
    client = make_client(settings, calls=calls)
    res = client.post("/join", json=FORM)
    assert res.status_code == 200
    assert calls == []
    assert "Иван Иванов" in caplog.text


def test_join_telegram_error_502(caplog):
    caplog.set_level(logging.DEBUG)
    client = make_client(
        configured(), handler=lambda r: httpx.Response(400, json={"ok": False, "description": "x"})
    )
    assert client.post("/join", json=FORM).status_code == 502
    assert TOKEN not in caplog.text


def test_join_telegram_timeout_502(caplog):
    caplog.set_level(logging.DEBUG)

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = make_client(configured(), handler=boom)
    assert client.post("/join", json=FORM).status_code == 502
    assert TOKEN not in caplog.text


def test_join_rate_limit_429_on_fourth():
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    headers = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    for _ in range(3):
        assert client.post("/join", json=FORM, headers=headers).status_code == 200
    assert client.post("/join", json=FORM, headers=headers).status_code == 429
    assert len(calls) == 3
    other = {"X-Forwarded-For": "198.51.100.1"}
    assert client.post("/join", json=FORM, headers=other).status_code == 200
