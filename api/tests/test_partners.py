import json
import logging

import httpx
import pytest
from bu_core.settings import Settings

from .test_join import FORM as JOIN_FORM
from .test_join import TOKEN, configured, make_client

FORM = {
    "about": "Магазин спортивной экипировки, готовы обсудить комплект формы",
    "contact": "partner@example.com",
    "website": "",
}


def test_partners_sends_one_message(caplog):
    caplog.set_level(logging.DEBUG)
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    res = client.post("/partners", json=FORM)
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert len(calls) == 1
    assert str(calls[0].url) == f"https://tg.test/bot{TOKEN}/sendMessage"
    body = json.loads(calls[0].content)
    assert body["chat_id"] == "42"
    assert body["text"] == (
        "🤝 Заявка на партнёрство\n"
        "Контакт: partner@example.com\n"
        "О себе и предложении:\n"
        "Магазин спортивной экипировки, готовы обсудить комплект формы"
    )
    assert TOKEN not in caplog.text


def test_partners_honeypot_not_sent():
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    res = client.post("/partners", json={**FORM, "website": "http://spam.example"})
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("about", "коротко"), ("about", "x" * 2001), ("contact", "ab"), ("contact", "x" * 201)],
)
def test_partners_invalid_data_422(field, value):
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    res = client.post("/partners", json={**FORM, field: value})
    assert res.status_code == 422
    assert any(err["loc"][-1] == field for err in res.json()["detail"])
    assert calls == []


def test_partners_missing_field_422():
    client = make_client(configured())
    assert client.post("/partners", json={"about": FORM["about"]}).status_code == 422


def test_partners_not_configured_503():
    client = make_client(
        Settings(
            telegram_bot_token=None, telegram_chat_id=None, join_chat_id=None, join_dry_run=False
        )
    )
    res = client.post("/partners", json=FORM)
    assert res.status_code == 503
    assert res.json() == {"detail": "partners is not configured"}


def test_partners_dry_run_does_not_send(caplog):
    caplog.set_level(logging.INFO)
    calls: list[httpx.Request] = []
    settings = Settings(telegram_bot_token=None, telegram_chat_id=None, join_dry_run=True)
    client = make_client(settings, calls=calls)
    assert client.post("/partners", json=FORM).status_code == 200
    assert calls == []
    assert "partner@example.com" in caplog.text


def test_partners_telegram_error_502(caplog):
    caplog.set_level(logging.DEBUG)
    client = make_client(
        configured(), handler=lambda r: httpx.Response(400, json={"ok": False, "description": "x"})
    )
    assert client.post("/partners", json=FORM).status_code == 502
    assert TOKEN not in caplog.text


def test_partners_telegram_timeout_502(caplog):
    caplog.set_level(logging.DEBUG)

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = make_client(configured(), handler=boom)
    assert client.post("/partners", json=FORM).status_code == 502
    assert TOKEN not in caplog.text


def test_partners_rate_limit_429_on_fourth_and_separate_from_join():
    calls: list[httpx.Request] = []
    client = make_client(configured(), calls=calls)
    headers = {"X-Forwarded-For": "203.0.113.7"}
    for _ in range(3):
        assert client.post("/partners", json=FORM, headers=headers).status_code == 200
    assert client.post("/partners", json=FORM, headers=headers).status_code == 429
    assert len(calls) == 3
    other = {"X-Forwarded-For": "198.51.100.1"}
    assert client.post("/partners", json=FORM, headers=other).status_code == 200
    # у формы «Хочу в команду» свой лимит
    assert client.post("/join", json=JOIN_FORM, headers=headers).status_code == 200
