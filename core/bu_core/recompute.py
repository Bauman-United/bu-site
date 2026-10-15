"""Пересчёт агрегатов, которые API только читает."""

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bu_core.models import (
    Computed,
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    Player,
    PlayerSeasonStats,
    PlayerTournamentStats,
    Season,
    Tournament,
)
from bu_core.stats import Result, StatLine, form, leaders, records, totals

FIELDS = ("played", "goals", "assists", "yellow", "red", "mvp")


def _put(session: Session, key: str, data: dict[str, Any]) -> None:
    row = session.get(Computed, key)
    if row is None:
        session.add(Computed(key=key, data=data))
    else:
        row.data = data


def _season_lines(session: Session) -> dict[tuple[int, int], dict[str, int]]:
    lines: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: dict.fromkeys(FIELDS, 0))

    rows = session.execute(
        select(PlayerTournamentStats, Tournament.season_id)
        .join(Tournament, Tournament.id == PlayerTournamentStats.tournament_id)
        .where(Tournament.source != "manual")
    )
    for stats, season_id in rows:
        line = lines[(stats.player_id, season_id)]
        for f in ("played", "goals", "assists", "yellow", "red"):
            line[f] += getattr(stats, f)

    manual = select(Match.id).join(Tournament).where(Tournament.source == "manual")
    for player_id, season_id in session.execute(
        select(MatchAppearance.player_id, Match.season_id)
        .join(Match, Match.id == MatchAppearance.match_id)
        .where(Match.id.in_(manual))
    ):
        lines[(player_id, season_id)]["played"] += 1
    for ev, season_id in session.execute(
        select(MatchEvent, Match.season_id)
        .join(Match, Match.id == MatchEvent.match_id)
        .where(Match.id.in_(manual), MatchEvent.team == "us")
    ):
        if ev.player_id and ev.type in ("goal", "penalty"):
            lines[(ev.player_id, season_id)]["goals"] += 1
        if ev.assist_id and ev.type in ("goal", "penalty"):
            lines[(ev.assist_id, season_id)]["assists"] += 1
        if ev.player_id and ev.type in ("yellow", "red"):
            lines[(ev.player_id, season_id)][ev.type] += 1

    for player_id, season_id in session.execute(
        select(Match.mvp_player_id, Match.season_id).where(Match.mvp_player_id.is_not(None))
    ):
        lines[(player_id, season_id)]["mvp"] += 1
    return lines


def recompute(session: Session) -> None:
    lines = _season_lines(session)
    session.execute(delete(PlayerSeasonStats))
    for (player_id, season_id), values in lines.items():
        session.add(PlayerSeasonStats(player_id=player_id, season_id=season_id, **values))
    session.flush()

    players = {p.id: p for p in session.scalars(select(Player))}
    seasons = {s.id: s for s in session.scalars(select(Season))}
    finished = session.scalars(select(Match).where(Match.status == "finished")).all()
    all_matches = session.scalars(select(Match).order_by(Match.kickoff)).all()

    now = datetime.now(UTC)
    current = None
    past_or_soon = [m for m in all_matches if m.kickoff <= now] or all_matches
    if past_or_soon:
        current = seasons[past_or_soon[-1].season_id].slug
    _put(session, "meta", {"current_season": current})

    for season in seasons.values():
        results = [
            Result(m.slug, m.kickoff, m.score_us or 0, m.score_them or 0)
            for m in finished
            if m.season_id == season.id
        ]
        stat_lines = [
            StatLine(
                pid,
                players[pid].slug,
                f"{players[pid].first_name} {players[pid].last_name}".strip(),
                **values,
            )
            for (pid, sid), values in lines.items()
            if sid == season.id
        ]
        _put(
            session,
            f"season:{season.slug}",
            {
                "form": form(results),
                "totals": totals(results),
                "leaders": {k: leaders(stat_lines, k) for k in ("goals", "assists", "mvp")},
            },
        )

    all_results = [Result(m.slug, m.kickoff, m.score_us or 0, m.score_them or 0) for m in finished]
    goal_minutes = [
        (slug, minute)
        for slug, minute in session.execute(
            select(Match.slug, MatchEvent.minute)
            .join(Match, Match.id == MatchEvent.match_id)
            .where(MatchEvent.team == "us", MatchEvent.type.in_(("goal", "penalty")))
        )
    ]
    appearances: dict[str, int] = defaultdict(int)
    for (pid, _sid), values in lines.items():
        p = players[pid]
        appearances[f"{p.first_name} {p.last_name}".strip()] += values["played"]

    club = session.get(ContentDoc, "club")
    history = session.get(ContentDoc, "history")
    trophies = (history.data.get("trophies") if history else None) or []
    _put(
        session,
        "club",
        {
            "records": records(all_results, goal_minutes, dict(appearances)),
            "numbers": {
                "founded": club.data.get("founded") if club else None,
                "matches": len(finished),
                "goals": sum(m.score_us or 0 for m in finished),
                "trophies": sum(1 for t in trophies if t.get("place") == 1),
            },
        },
    )
    session.flush()
