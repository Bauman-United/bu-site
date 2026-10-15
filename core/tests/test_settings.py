from bu_core.settings import Settings


def test_settings_use_bu_prefix_and_ignore_foreign_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "foreign")
    monkeypatch.setenv("BU_TELEGRAM_CHAT_ID", "42")
    s = Settings(_env_file=None)
    assert s.telegram_bot_token is None
    assert s.telegram_chat_id == "42"
