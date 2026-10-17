import time
import urllib.robotparser

import httpx


class DisallowedError(Exception):
    pass


class PoliteClient:
    """HTTP-клиент, который уважает robots.txt и не торопится."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        delay_s: float,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "User-Agent": user_agent,
                # lfl.ru drops requests with httpx's minimal default Accept header.
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            },
            timeout=20.0,
            follow_redirects=True,
            transport=transport,
        )
        self._agent = user_agent.split("/")[0]
        self._delay = delay_s
        self._last = 0.0
        self._robots: urllib.robotparser.RobotFileParser | None = None
        # Python не сверяет wildcard-сертификат с именем, где есть «_» (bauman_league.*):
        # проверяем цепочку и имя по эквивалентному хосту с «-», Host остаётся настоящим.
        host = httpx.URL(base_url).host
        self._extensions = {"sni_hostname": host.replace("_", "-")} if "_" in host else {}

    def _fetch(self, method: str, path: str, json: dict | None = None) -> httpx.Response:
        request = self._client.build_request(method, path, json=json, extensions=self._extensions)
        return self._client.send(request)

    def _wait(self) -> None:
        pause = self._delay - (time.monotonic() - self._last)
        if pause > 0:
            time.sleep(pause)
        self._last = time.monotonic()

    def _allowed(self, path: str) -> bool:
        if self._robots is None:
            self._robots = urllib.robotparser.RobotFileParser()
            self._wait()
            response = self._fetch("GET", "/robots.txt")
            lines = response.text.splitlines() if response.status_code == 200 else []
            self._robots.parse(lines)
        return self._robots.can_fetch(self._agent, path)

    def _request(self, method: str, path: str, json: dict | None = None) -> str:
        if not self._allowed(path):
            raise DisallowedError(path)
        last_error: Exception | None = None
        for attempt in range(3):
            self._wait()
            try:
                response = self._fetch(method, path, json)
                if response.status_code < 500:
                    response.raise_for_status()
                    return response.text
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )
            except httpx.TransportError as exc:
                last_error = exc
            time.sleep(min(2**attempt, 8) if self._delay else 0)
        assert last_error is not None
        raise last_error

    def get(self, path: str) -> str:
        return self._request("GET", path)

    def post(self, path: str, json: dict) -> str:
        return self._request("POST", path, json)
