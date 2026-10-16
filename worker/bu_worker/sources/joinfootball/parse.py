"""Чистые функции: HTML страниц join.football -> DTO. Сеть здесь не используется."""

import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

from bu_worker.dto import (
    CalendarEntry,
    MatchDetail,
    ParsedEvent,
    ParsedPlayer,
    ParsedStanding,
    Side,
    TournamentInfo,
)

MSK = ZoneInfo("Europe/Moscow")
MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
POSITIONS = {"Вр.": "GK", "Зщ.": "DF", "Пз.": "MF", "Нп.": "FW"}
_PERIOD = re.compile(r"(\d{1,2}) ([а-я]+) (\d{4}) - (\d{1,2}) ([а-я]+) (\d{4})")
_DAY = re.compile(r"(\d{1,2}) ([а-я]+)")
_SCORE = re.compile(r"(\d+)\s*[-:]\s*(\d+)")
_CLOCK = re.compile(r"(\d{1,2}):(\d{2})")
_TEAM_ID = re.compile(r"team_id=(\d+)")
_UNDATED = "не задано"
_LAST_ID = re.compile(r"/(\d+)(?:\?|$)")


_SIZE_SUFFIX = re.compile(r"_\d+x\d+(?=\.\w+$)")


def full_size(url: str | None) -> str | None:
    """CDN joinsport отдаёт превью «…_60x60.jpg»; без суффикса — оригинал (его ужмёт next/image)."""
    return _SIZE_SUFFIX.sub("", url) if url else None


class ParseError(Exception):
    pass


def _text(node: Node | None) -> str:
    return node.text(strip=True) if node is not None else ""


def _int(value: str) -> int:
    value = value.strip()
    return int(value) if value.isdigit() else 0


def _lead_int(value: str) -> int:
    """«17 (1)» — голы (из них с пенальти) → 17; «-» → 0."""
    m = re.match(r"\s*(\d+)", value)
    return int(m[1]) if m else 0


def _attr(node: Node | None, name: str) -> str | None:
    if node is None:
        return None
    return node.attributes.get(name)


def _date_in_period(day: int, month_name: str, start: date, end: date) -> date:
    month = MONTHS[month_name]
    for year in range(start.year, end.year + 1):
        candidate = date(year, month, day)
        if start <= candidate <= end:
            return candidate
    return date(start.year, month, day)


def parse_tournament_info(html: str, external_id: str, url: str) -> TournamentInfo:
    tree = HTMLParser(html)
    title = _text(tree.css_first(".blk-tournamentheader__title"))
    dates = _text(tree.css_first(".blk-tournamentheader__info-dates"))
    m = _PERIOD.search(dates)
    if not title or not m:
        raise ParseError("tournament header not found")
    start = date(int(m[3]), MONTHS[m[2]], int(m[1]))
    end = date(int(m[6]), MONTHS[m[5]], int(m[4]))
    name = " · ".join(part.strip() for part in title.split("|"))
    return TournamentInfo(
        external_id=external_id, name=name, period_start=start, period_end=end, url=url
    )


def parse_application(html: str, departed: bool = False) -> list[ParsedPlayer]:
    """Первая таблица — текущая заявка. `departed` — ещё и «Отзаявленные игроки» (active=False):
    для прошлых турниров их голы и игры тоже часть истории.
    """
    tree = HTMLParser(html)
    tables = tree.css("table.blk-tteams__table")
    rows = tables[0].css("tr.blk-tteams__row") if tables else []
    if not rows:
        raise ParseError("application table not found")
    tagged = [(row, True) for row in rows]
    if departed and len(tables) > 1:
        tagged += [(row, False) for row in tables[1].css("tr.blk-tteams__row")]
    players: list[ParsedPlayer] = []
    seen: set[str] = set()
    for row, active in tagged:
        link = row.css_first("a.blk-tteams__player")
        href = _attr(link, "href") or ""
        id_match = _LAST_ID.search(href)
        name = _text(row.css_first(".blk-tteams__player-name"))
        if not id_match or not name or id_match[1] in seen:
            continue
        seen.add(id_match[1])
        number_text = _text(row.css_first(".blk-tteams__cell--number"))
        stats = [_lead_int(_text(cell)) for cell in row.css(".blk-tteams__cell--var")]
        stats += [0] * (5 - len(stats))
        players.append(
            ParsedPlayer(
                external_id=id_match[1],
                full_name=name,
                number=int(number_text) if number_text.isdigit() else None,
                position=POSITIONS.get(_text(row.css_first(".blk-tteams__cell--amplua"))),
                played=stats[0],
                goals=stats[1],
                assists=stats[2],
                yellow=stats[3],
                red=stats[4],
                photo_url=full_size(_attr(row.css_first("img.blk-tteams__player-img"), "src")),
                active=active,
            )
        )
    if not players:
        raise ParseError("no players parsed")
    return players


def _team_side(item: Node, side: str) -> tuple[str, str, str | None]:
    team = item.css_first(f".blk-tcalendar__team--{side}")
    team_id_match = _TEAM_ID.search(_attr(team, "href") or "")
    name = _text(team.css_first(".blk-tcalendar__team-name")) if team is not None else ""
    logo = full_size(_attr(team.css_first("img"), "src")) if team is not None else None
    return (team_id_match[1] if team_id_match else ""), name, logo


def parse_calendar(html: str, period_start: date, period_end: date) -> list[CalendarEntry]:
    tree = HTMLParser(html)
    entries: dict[str, CalendarEntry] = {}
    for unit in tree.css(".blk-tcalendar__unit"):
        head = _text(unit.css_first(".blk-tcalendar__head-text"))
        day_match = _DAY.search(head)
        day: date | None
        if day_match:
            day = _date_in_period(int(day_match[1]), day_match[2], period_start, period_end)
        elif head.lower() == _UNDATED:
            day = None  # «Не задано»: матч назначен, дата ещё не известна
        else:
            continue
        for item in unit.css("li.blk-tcalendar__item"):
            score_link = item.css_first("a.blk-tcalendar__score")
            match_id = _LAST_ID.search(_attr(score_link, "href") or "")
            if not match_id:
                continue
            clock = _CLOCK.search(_text(item.css_first(".blk-tcalendar__time")))
            hh, mm = (clock[1], clock[2]) if clock else ("0", "0")  # «Перенесён», «--:--»
            place = item.css_first(".blk-tcalendar__place")
            score = _SCORE.search(_text(item.css_first(".blk-tcalendar__score-main")))
            home_id, home_name, home_logo = _team_side(item, "left")
            away_id, away_name, away_logo = _team_side(item, "right")
            entries[match_id[1]] = CalendarEntry(
                external_id=match_id[1],
                kickoff=datetime.combine(day, time(int(hh), int(mm)), tzinfo=MSK)
                if day is not None
                else None,
                round=_text(item.css_first(".blk-tcalendar__round")) or None,
                venue_name=_text(item.css_first(".blk-tcalendar__place-name")) or None,
                venue_address=_attr(place, "title"),
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


def _event_type(classes: list[str]) -> tuple[str, str | None] | None:
    if "goal" in classes:
        return "goal", None
    if "goal-standard" in classes:
        return "goal", "со стандарта"
    if "penalty" in classes or "goal-penalty" in classes:
        return "penalty", None
    if "autogoal" in classes or "own-goal" in classes:
        return "own_goal", None
    if "yellow-card" in classes:
        return "yellow", None
    if "red-card" in classes or "second-yellow-card" in classes:
        return "red", None
    return None


def parse_match(html: str) -> MatchDetail:
    tree = HTMLParser(html)
    if tree.css_first(".blk-matchheader") is None:
        raise ParseError("match header not found")
    events: list[ParsedEvent] = []
    for node in tree.css(".game-timeline__event"):
        classes = (_attr(node, "class") or "").split()
        kind = _event_type(classes)
        minute_text = (_attr(node, "data-time") or "").strip().rstrip("'").split("+")[0]
        if kind is None or not minute_text.isdigit():
            continue
        if "team1" not in classes and "team2" not in classes:
            raise ParseError("event without team side")
        side: Side = "home" if "team1" in classes else "away"
        events.append(
            ParsedEvent(
                minute=int(minute_text),
                type=kind[0],  # type: ignore[arg-type]
                side=side,
                player_name=_attr(node, "data-player-first"),
                assist_name=_attr(node, "data-player-second"),
                note=kind[1],
            )
        )
    events.sort(key=lambda e: e.minute)
    score = [_int(_text(n)) for n in tree.css(".blk-matchheader__score-item") if _text(n)]
    if sum(score) > 0 and not any(e.type in ("goal", "penalty", "own_goal") for e in events):
        raise ParseError("score has goals but timeline is missing")

    mvp_name: str | None = None
    mvp_side: Side | None = None
    for index, unit in enumerate(tree.css(".blk-matchheader__unit")):
        best = unit.css_first(".blk-matchheader__best-name")
        if best is not None:
            mvp_name = _text(best)
            mvp_side = "home" if index == 0 else "away"
    return MatchDetail(events=events, mvp_name=mvp_name, mvp_side=mvp_side)


def parse_standings(html: str) -> list[ParsedStanding]:
    tree = HTMLParser(html)
    table = tree.css_first(".custom-table-table")
    if table is None:
        raise ParseError("standings table not found")
    rows: list[ParsedStanding] = []
    for line in table.css("li.custom-table__line"):
        values = [_text(cell) for cell in line.css(".custom-table__var")]
        pos = _text(line.css_first(".custom-table__number-wrapper"))
        if len(values) < 6 or not pos.isdigit():
            continue
        goals = _SCORE.search(values[4])
        rows.append(
            ParsedStanding(
                pos=int(pos),
                team_name=_text(line.css_first(".custom-table__team-name")),
                team_logo=_attr(line.css_first(".custom-table__team-img"), "src"),
                played=_int(values[0]),
                won=_int(values[1]),
                drawn=_int(values[2]),
                lost=_int(values[3]),
                gf=int(goals[1]) if goals else 0,
                ga=int(goals[2]) if goals else 0,
                pts=_int(values[5]),
            )
        )
    if not rows:
        raise ParseError("standings are empty")
    return rows
