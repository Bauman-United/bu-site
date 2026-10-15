import logging
import time

import httpx

log = logging.getLogger(__name__)
COOLDOWN_S = 6 * 3600


class Notifier:
    def __init__(
        self, token: str | None, chat_id: str | None, transport: httpx.BaseTransport | None = None
    ):
        self._token, self._chat_id = token, chat_id
        self._transport = transport
        self._sent: dict[str, float] = {}

    def send(self, text: str, key: str) -> None:
        log.warning("alert [%s]: %s", key, text)
        if not self._token or not self._chat_id:
            return
        now = time.monotonic()
        if now - self._sent.get(key, -COOLDOWN_S) < COOLDOWN_S:
            return
        self._sent[key] = now
        try:
            with httpx.Client(transport=self._transport, timeout=10) as client:
                client.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage",
                    json={"chat_id": self._chat_id, "text": f"⚠️ bu-site: {text}"},
                )
        except httpx.HTTPError:
            log.exception("telegram alert failed")
