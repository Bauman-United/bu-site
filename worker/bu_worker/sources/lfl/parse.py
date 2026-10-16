"""Чистые функции: HTML страниц lfl.ru -> общие DTO воркера."""

import re
from collections.abc import Callable
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from bu_core.text import normalize_name
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

from bu_worker.dto import (
    CalendarEntry,
    EventType,
    MatchDetail,
    ParsedEvent,
    ParsedPlayer,
    ParsedStanding,
    Side,
    TournamentInfo,
)

MSK = ZoneInfo("Europe/Moscow")
POSITIONS = {
    "вратарь": "GK",
    "защитник": "DF",
    "полузащитник": "MF",
    "нападающий": "FW",
}
_PLAYER_ID = re.compile(r"/player(\d+)")
_CLUB_ID = re.compile(r"/club(\d+)")
_MATCH_ID = re.compile(r"/match(\d+)")
_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_CLOCK = re.compile(r"(\d{1,2}):(\d{2})")
_SCORE = re.compile(r"(\d+)\s*:\s*(\d+)")
_COUNT = re.compile(r"\((\d+)\)\s*;?$")
_MINUTE = re.compile(r"(\d+)\s*'")
_YEAR = re.compile(r"(?:19|20)\d{2}")


class ParseError(Exception):
    pass


def _text(node: Node | None) -> str:
    return " ".join(node.text(strip=True).split()) if node is not None else ""


def _attr(node: Node | None, name: str) -> str | None:
    return node.attributes.get(name) if node is not None else None


def _int(value: str) -> int:
    value = value.strip()
    return int(value) if value.isdigit() else 0


def _id(node: Node | None, pattern: re.Pattern[str]) -> str:
    match = pattern.search(_attr(node, "href") or "")
    return match[1] if match else ""


def parse_tournament_info(html: str, external_id: str, url: str) -> TournamentInfo:
    tree = HTMLParser(html)
    name = _text(tree.css_first(".league_text"))
    years = [int(value) for value in _YEAR.findall(name)]
    if not name or not years:
        raise ParseError("tournament header not found")
    return TournamentInfo(
        external_id=external_id,
        name=name,
        # Турнир ЛФЛ с меткой «2026» идёт весь календарный год — сезон 2026.
        period_start=date(min(years), 1, 1),
        period_end=date(max(years), 12, 31),
        url=url,
    )


def parse_season_id(html: str) -> str:
    tree = HTMLParser(html)
    node = tree.css_first("[season_id]")
    season_id = _attr(node, "season_id")
    if not season_id or not season_id.isdigit():
        raise ParseError("tournament season id not found")
    return season_id


def parse_current_player_ids(html: str) -> set[str]:
    tree = HTMLParser(html)
    ids = {
        player_id
        for link in tree.css(".club-player-list a[href*='/player']")
        if (player_id := _id(link, _PLAYER_ID))
    }
    if not ids:
        raise ParseError("current club roster not found")
    return ids


def parse_players(html: str, current_player_ids: set[str] | None = None) -> list[ParsedPlayer]:
    tree = HTMLParser(html)
    table = tree.css_first("table.tournament_squads_table")
    if table is None:
        raise ParseError("squad table not found")
    players: list[ParsedPlayer] = []
    current_position: str | None = None
    for row in table.css("tbody tr"):
        heading = row.css_first(".tour-header")
        if heading is not None:
            current_position = POSITIONS.get(_text(heading).lower())
            continue
        player_link = row.css_first("a.player")
        external_id = _id(player_link, _PLAYER_ID)
        name = _text(player_link)
        cells = row.css("td")
        if not external_id or not name or len(cells) < 8:
            continue
        position = POSITIONS.get(_text(row.css_first(".amplua")).lower(), current_position)
        players.append(
            ParsedPlayer(
                external_id=external_id,
                full_name=name,
                number=None,  # первый столбец LFL — номер строки внутри амплуа, не игровой номер
                position=position,
                played=_int(_text(cells[2])),
                goals=_int(_text(cells[3])),
                assists=_int(_text(cells[4])),
                yellow=_int(_text(cells[5])),
                red=_int(_text(cells[6])) + _int(_text(cells[7])),
                active=current_player_ids is None or external_id in current_player_ids,
            )
        )
    if not players:
        raise ParseError("no players parsed")
    return players


def _team(cell: Node) -> tuple[str, str, str | None]:
    link = cell.css_first("a[href*='/club']")
    return (
        _id(link, _CLUB_ID),
        (_attr(link, "title") or _text(link)).strip(),
        _attr(cell.css_first("img"), "src"),
    )


def parse_calendar(html: str, tournament_id: str | None = None) -> list[CalendarEntry]:
    tree = HTMLParser(html)
    table = tree.css_first("table.league_tournament_calendar_table")
    if table is None:
        raise ParseError("calendar table not found")
    entries: dict[str, CalendarEntry] = {}
    round_name: str | None = None
    for row in table.css("tbody tr"):
        heading = row.css_first(".tour-header")
        if heading is not None:
            round_name = _text(heading) or None
            continue
        cells = row.css("td")
        if len(cells) < 7:
            continue
        tournament_link = cells[6].css_first("a[href*='/tournament']")
        if tournament_id and f"/tournament{tournament_id}" not in (
            _attr(tournament_link, "href") or ""
        ):
            continue
        match_link = row.css_first("a[href*='/match']")
        external_id = _id(match_link, _MATCH_ID)
        day_match = _DATE.search(_text(cells[0]))
        if not external_id or not day_match:
            continue  # матчи без назначенной даты пока нельзя показать в календаре сайта
        clock = _CLOCK.search(_text(cells[1]))
        kickoff = datetime.combine(
            date(int(day_match[3]), int(day_match[2]), int(day_match[1])),
            time(int(clock[1]), int(clock[2])) if clock else time(),
            tzinfo=MSK,
        )
        home_id, home_name, home_logo = _team(cells[2])
        away_id, away_name, away_logo = _team(cells[4])
        score = _SCORE.search(_text(cells[3]))
        venue_link = cells[5].css_first("a")
        entries[external_id] = CalendarEntry(
            external_id=external_id,
            kickoff=kickoff,
            round=round_name,
            venue_name=_text(venue_link) or _text(cells[5]) or None,
            venue_address=None,
            home_team_id=home_id,
            away_team_id=away_id,
            home_name=home_name,
            away_name=away_name,
            home_logo=home_logo,
            away_logo=away_logo,
            home_score=int(score[1]) if score else None,
            away_score=int(score[2]) if score else None,
        )
    if not entries:
        raise ParseError("calendar is empty")
    return list(entries.values())


def parse_standings(html: str) -> list[ParsedStanding]:
    tree = HTMLParser(html)
    table = tree.css_first("table.tournament_table")
    if table is None:
        raise ParseError("standings table not found")
    rows: list[ParsedStanding] = []
    for row in table.css("tbody tr"):
        cells = row.css("td")
        if len(cells) < 11 or not _text(cells[0]).isdigit():
            continue
        rows.append(
            ParsedStanding(
                pos=int(_text(cells[0])),
                team_name=_text(cells[2]),
                team_logo=_attr(cells[1].css_first("img"), "src"),
                played=_int(_text(cells[3])),
                won=_int(_text(cells[4])),
                drawn=_int(_text(cells[5])),
                lost=_int(_text(cells[6])),
                gf=_int(_text(cells[7])),
                ga=_int(_text(cells[8])),
                pts=_int(_text(cells[10])),
            )
        )
    if not rows:
        raise ParseError("standings are empty")
    return rows


def _side(club_id: str, home_id: str, away_id: str) -> Side | None:
    if club_id == home_id:
        return "home"
    if club_id == away_id:
        return "away"
    return None


def _section_blocks(match: Node) -> list[tuple[str, Node]]:
    result: list[tuple[str, Node]] = []
    for heading in match.css(".match_right_head"):
        block = heading.next
        while block is not None and "match_members" not in (_attr(block, "class") or "").split():
            block = block.next
        if block is not None:
            result.append((_text(heading).rstrip(":"), block))
    return result


def parse_match(html: str) -> MatchDetail:
    tree = HTMLParser(html)
    match = tree.css_first(".some_news[id^='match']")
    if match is None:
        raise ParseError("match protocol not found")
    home_id = _id(match.css_first(".match_team_home a[href*='/club']"), _CLUB_ID)
    away_id = _id(match.css_first(".match_team_away a[href*='/club']"), _CLUB_ID)
    scores = [_int(_text(node)) for node in match.css(".match_score")]
    score_total = sum(scores[::2]) if len(scores) >= 3 else 0
    events: list[ParsedEvent] = []
    for title, block in _section_blocks(match):
        if title == "Голы":
            current_side: Side | None = None
            for node in block.css("p, a[href*='/player']"):
                club_link = node.css_first("a.match_members_club") if node.tag == "p" else None
                if club_link is not None:
                    current_side = _side(_id(club_link, _CLUB_ID), home_id, away_id)
                    continue
                if current_side is None or node.tag != "a":
                    continue
                raw_name = _text(node)
                count = _COUNT.search(raw_name)
                player_name = _COUNT.sub("", raw_name).strip()
                for _ in range(int(count[1]) if count else 1):
                    events.append(
                        ParsedEvent(
                            minute=0,
                            type="goal",
                            side=current_side,
                            player_name=player_name,
                            note="минута не указана",
                        )
                    )
        elif title in {"Предупреждения", "Удаления"}:
            for item in block.css("span"):
                player = item.css_first("a[href*='/player']")
                club = item.css_first("a[href*='/club']")
                side = _side(_id(club, _CLUB_ID), home_id, away_id)
                icon = _attr(item.css_first("img[src*='popup_']"), "src") or ""
                if player is None or side is None:
                    continue
                kind: EventType = "red" if "popup_rc" in icon or "popup_2yc" in icon else "yellow"
                minute = _MINUTE.search(_text(item))
                events.append(
                    ParsedEvent(
                        minute=int(minute[1]) if minute else 0,
                        type=kind,
                        side=side,
                        player_name=_text(player).removesuffix("(").strip(),
                        note="минута не указана" if not minute or minute[1] == "0" else None,
                    )
                )
    goals = sum(event.type in {"goal", "penalty", "own_goal"} for event in events)
    # Технические результаты (обычно 5:0) публикуются вообще без авторов голов.
    if score_total and goals and goals != score_total:
        raise ParseError(f"parsed {goals} goals for score total {score_total}")
    events.sort(key=lambda event: event.minute)
    return MatchDetail(events=events)


_NAME_WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")


def _name_key(full_name: str) -> str | None:
    """«Королёв Александр Дмитриевич» -> «королев александр» (фамилия + имя, без отчества)."""
    words = _NAME_WORD.findall(full_name)
    return normalize_name(" ".join(words[:2])) if len(words) >= 2 else None


def parse_player_photos(html: str) -> dict[str, str]:
    """Страница «Подробный список» клуба: фото игроков по ключу «фамилия имя»."""
    tree = HTMLParser(html)
    photos: dict[str, str] = {}
    last_logo: str | None = None
    for node in tree.css(".player_logo, .player_title_name"):
        classes = (node.attributes.get("class") or "").split()
        if "player_logo" in classes:
            last_logo = _attr(node.css_first("img"), "src")
            continue
        key = _name_key(_text(node))
        if key and last_logo:
            photos[key] = last_logo.replace("http://", "https://", 1)
        last_logo = None
    return photos


def attach_photos(players: list[ParsedPlayer], photos: dict[str, str]) -> list[ParsedPlayer]:
    return [
        p.model_copy(update={"photo_url": photos.get(_name_key(p.full_name) or "")})
        for p in players
    ]


def fill_missing_photos(
    players: list[ParsedPlayer], fetch_player_page: Callable[[str], str]
) -> list[ParsedPlayer]:
    """Бывших игроков нет в «Подробном списке» — берём фото с их личной страницы."""
    out: list[ParsedPlayer] = []
    for p in players:
        if p.photo_url is None:
            photos = parse_player_photos(fetch_player_page(p.external_id))
            key = _name_key(p.full_name) or ""
            p = p.model_copy(update={"photo_url": photos.get(key)})
        out.append(p)
    return out


_CLUB_TOURNAMENT = re.compile(r"^#tournament_(\d+)$")


def parse_club_tournament_ids(html: str) -> list[str]:
    """Турниры клуба из селектора на странице /club<id> («#tournament_32573»).

    Нечисловые («#tournament_d1037» — Летний кубок), «Все» и служебный «Тест» пропускаем.
    """
    ids: list[str] = []
    for link in HTMLParser(html).css("a.tournament_selector_item"):
        m = _CLUB_TOURNAMENT.match(link.attributes.get("href") or "")
        title = (link.attributes.get("title") or link.text(strip=True)).strip().lower()
        # «#tournament_0» — вкладка «Все»
        if m and m[1] != "0" and title != "тест" and m[1] not in ids:
            ids.append(m[1])
    return ids
