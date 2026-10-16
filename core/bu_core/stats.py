"""Чистые функции командной и игровой статистики (см. 03-data-model.md пакета)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

Outcome = Literal["W", "D", "L"]


@dataclass(frozen=True)
class Result:
    slug: str
    kickoff: datetime | None  # None — дата неизвестна, такие идут последними
    us: int
    them: int


@dataclass(frozen=True)
class StatLine:
    player_id: int
    slug: str
    name: str
    played: int
    goals: int
    assists: int
    yellow: int
    red: int
    mvp: int
    photo: str | None = None
    number: int | None = None


def outcome(us: int, them: int) -> Outcome:
    if us > them:
        return "W"
    return "D" if us == them else "L"


def _chrono(results: list[Result]) -> list[Result]:
    return sorted(results, key=lambda x: (x.kickoff is None, x.kickoff or datetime.min))


def form(results: list[Result], n: int = 5) -> list[dict[str, Any]]:
    return [
        {"slug": x.slug, "outcome": outcome(x.us, x.them), "us": x.us, "them": x.them}
        for x in _chrono(results)[-n:]
    ]


def totals(results: list[Result]) -> dict[str, int]:
    outcomes = [outcome(x.us, x.them) for x in results]
    return {
        "played": len(results),
        "won": outcomes.count("W"),
        "drawn": outcomes.count("D"),
        "lost": outcomes.count("L"),
        "gf": sum(x.us for x in results),
        "ga": sum(x.them for x in results),
        "clean_sheets": sum(1 for x in results if x.them == 0),
    }


def leaders(lines: list[StatLine], key: str, n: int = 5) -> list[dict[str, Any]]:
    ranked = sorted(
        (line for line in lines if getattr(line, key) > 0),
        key=lambda line: (-getattr(line, key), line.played, line.name),
    )
    return [
        {
            "slug": line.slug,
            "name": line.name,
            "value": getattr(line, key),
            "played": line.played,
            "photo": line.photo,
            "number": line.number,
        }
        for line in ranked[:n]
    ]


def records(
    results: list[Result],
    goal_minutes: list[tuple[str, int]],
    appearances: dict[str, int],
) -> dict[str, Any]:
    chrono = _chrono(results)
    wins = [x for x in chrono if x.us > x.them]
    biggest = max(wins, key=lambda x: (x.us - x.them, x.us), default=None)

    best: tuple[int, str, str] | None = None
    run: list[Result] = []
    for x in chrono:
        if x.us >= x.them:
            run.append(x)
            if best is None or len(run) > best[0]:
                best = (len(run), run[0].slug, run[-1].slug)
        else:
            run = []

    fastest = min(goal_minutes, key=lambda g: g[1], default=None)
    most = max(appearances.items(), key=lambda kv: kv[1], default=None)
    return {
        "biggest_win": {"slug": biggest.slug, "us": biggest.us, "them": biggest.them}
        if biggest
        else None,
        "unbeaten_streak": {"length": best[0], "from": best[1], "to": best[2]} if best else None,
        "fastest_goal": {"slug": fastest[0], "minute": fastest[1]} if fastest else None,
        "most_appearances": {"name": most[0], "value": most[1]} if most else None,
    }
