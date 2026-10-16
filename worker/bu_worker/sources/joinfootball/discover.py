"""Поиск всех турниров команды на платформе joinsport (Bauman League, IFL, Urban Cup) по сезонам."""

import re

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from bu_worker.http import PoliteClient

_TOURNAMENT = re.compile(r"^/tournament/(\d+)/")


def parse_season_ids(html: str, team_id: str) -> list[str]:
    """Ссылки «Осень 2026 … Осень 2015» на /team/<id>/calendar?season_id=… — новые первыми."""
    pattern = re.compile(rf"/team/{re.escape(team_id)}/calendar\?season_id=(\d+)$")
    ids: list[str] = []
    for link in HTMLParser(html).css("a[href]"):
        m = pattern.search(link.attributes.get("href") or "")
        if m and m[1] not in ids:
            ids.append(m[1])
    return ids


def parse_season_tournament_ids(html: str) -> list[str]:
    """Турниры из матчей календаря команды за сезон.

    Сайдбар каждой страницы ссылается на текущие турниры лиги — их не берём: только команды
    в строках расписания (`.blk-lschedule__team` → /tournament/<id>/teams/application…).
    """
    ids: list[str] = []
    for link in HTMLParser(html).css(".blk-lschedule__item a.blk-lschedule__team"):
        m = _TOURNAMENT.match(link.attributes.get("href") or "")
        if m and m[1] not in ids:
            ids.append(m[1])
    return ids


def discover_tournament_seasons(client: PoliteClient, team_id: str) -> dict[str, str]:
    """Все турниры, где играла команда, → сезон (season_id), от старых сезонов к новым."""
    seasons = parse_season_ids(client.get(f"/team/{team_id}/calendar"), team_id)
    found: dict[str, str] = {}
    for season_id in reversed(seasons):
        html = client.get(f"/team/{team_id}/calendar?season_id={season_id}")
        for tid in parse_season_tournament_ids(html):
            found.setdefault(tid, season_id)
    return found


def discover_tournaments(client: PoliteClient, team_id: str) -> list[str]:
    """Все турниры, где играла команда, от старых сезонов к новым."""
    return list(discover_tournament_seasons(client, team_id))
