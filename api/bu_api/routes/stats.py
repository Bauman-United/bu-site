from collections import defaultdict
from typing import Any

from bu_core.models import (
    Computed,
    Match,
    Player,
    PlayerSeasonStats,
    PlayerTournamentStats,
    Season,
)
from bu_core.stats import StatLine, leaders
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, full_name
from bu_api.schemas import AllTimeRecords, GoalkeeperRecord, RecordRow

router = APIRouter()
KEYS = ("played", "goals", "assists", "yellow", "red", "mvp")


@router.get("/stats")
def stats(season: str | None = None, session: Session = Depends(get_session)) -> dict[str, Any]:
    season = season or current_season(session) or "all"
    query = select(PlayerSeasonStats, Season.slug).join(Season)
    if season != "all":
        query = query.where(Season.slug == season)
    sums: dict[int, dict[str, int]] = defaultdict(lambda: dict.fromkeys(KEYS, 0))
    for row, _slug in session.execute(query):
        for k in KEYS:
            sums[row.player_id][k] += getattr(row, k)
    players = {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(sums)))}
    lines = [
        StatLine(
            pid,
            players[pid].slug,
            full_name(players[pid]),
            **v,
            photo=players[pid].photo,
            number=players[pid].number,
        )
        for pid, v in sums.items()
    ]
    table = sorted(
        (
            {
                "slug": players[pid].slug,
                "name": full_name(players[pid]),
                "position": players[pid].position,
                **v,
                "ga": v["goals"] + v["assists"],
            }
            for pid, v in sums.items()
        ),
        key=lambda r: (-int(r["goals"] or 0), -int(r["assists"] or 0), str(r["name"])),
    )
    seasons_out = []
    for s in session.scalars(select(Season).order_by(Season.slug)):
        finished = session.scalars(
            select(Match).where(Match.season_id == s.id, Match.status == "finished")
        ).all()
        seasons_out.append(
            {
                "slug": s.slug,
                "label": s.label,
                "gf": sum(m.score_us or 0 for m in finished),
                "ga": sum(m.score_them or 0 for m in finished),
                "final_place": s.final_place,
            }
        )
    club = session.get(Computed, "club")
    return {
        "season": season,
        "leaders": {k: leaders(lines, k) for k in ("goals", "assists", "mvp")},
        "players": table,
        "records": club.data["records"] if club else {},
        "seasons": seasons_out,
    }


RECORD_KEYS = ("goals", "assists", "played")


@router.get("/records/all-time")
def all_time_records(
    limit: int = Query(10, ge=1, le=100), session: Session = Depends(get_session)
) -> AllTimeRecords:
    """Суммы PlayerSeasonStats по всем сезонам (все турниры и источники), включая бывших
    игроков. Ничья — выше тот, у кого меньше матчей, затем по имени; нули не попадают.
    """
    sums: dict[int, dict[str, int]] = defaultdict(lambda: dict.fromkeys(RECORD_KEYS, 0))
    for row in session.scalars(select(PlayerSeasonStats)):
        for k in RECORD_KEYS:
            sums[row.player_id][k] += getattr(row, k) or 0
    players = {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(sums)))}

    def top(key: str) -> list[RecordRow]:
        ranked = sorted(
            (pid for pid, v in sums.items() if v[key] > 0),
            key=lambda pid: (-sums[pid][key], sums[pid]["played"], full_name(players[pid])),
        )[:limit]
        return [
            RecordRow(
                rank=i,
                slug=players[pid].slug,
                name=full_name(players[pid]),
                photo=players[pid].photo,
                position=players[pid].position,
                value=sums[pid][key],
                played=sums[pid]["played"],
                active=players[pid].active,
            )
            for i, pid in enumerate(ranked, start=1)
        ]

    # Источники дают число игр каждого вратаря по турниру, но не всегда сохраняют полные
    # протоколы старых матчей. Поэтому пропущенные в турнире распределяем пропорционально
    # сыгранным матчам: это сохраняет реальное число игр и средний показатель команды.
    goalkeeper_totals: dict[int, dict[str, int]] = defaultdict(lambda: {"played": 0, "conceded": 0})
    tournament_scores: dict[int, tuple[int, int]] = {}
    for match in session.scalars(
        select(Match).where(
            Match.status == "finished",
            Match.score_us.is_not(None),
            Match.score_them.is_not(None),
        )
    ):
        games, conceded = tournament_scores.get(match.tournament_id, (0, 0))
        tournament_scores[match.tournament_id] = (games + 1, conceded + (match.score_them or 0))

    goalkeeper_rows = session.execute(
        select(PlayerTournamentStats, Player)
        .join(Player, Player.id == PlayerTournamentStats.player_id)
        .where(Player.position == "GK", PlayerTournamentStats.played > 0)
    )
    for stats_row, _player in goalkeeper_rows:
        tournament_games, tournament_conceded = tournament_scores.get(
            stats_row.tournament_id, (0, 0)
        )
        if tournament_games == 0:
            continue
        played = stats_row.played or 0
        goalkeeper_totals[stats_row.player_id]["played"] += played
        goalkeeper_totals[stats_row.player_id]["conceded"] += round(
            tournament_conceded * played / tournament_games
        )

    goalkeeper_players = {
        p.id: p for p in session.scalars(select(Player).where(Player.id.in_(goalkeeper_totals)))
    }
    eligible = [
        player_id for player_id, values in goalkeeper_totals.items() if values["played"] > 10
    ]
    eligible.sort(
        key=lambda player_id: (
            goalkeeper_totals[player_id]["conceded"] / goalkeeper_totals[player_id]["played"],
            -goalkeeper_totals[player_id]["played"],
            full_name(goalkeeper_players[player_id]),
        )
    )
    goalkeepers = [
        GoalkeeperRecord(
            rank=rank,
            slug=goalkeeper_players[player_id].slug,
            name=full_name(goalkeeper_players[player_id]),
            photo=goalkeeper_players[player_id].photo,
            played=goalkeeper_totals[player_id]["played"],
            conceded=goalkeeper_totals[player_id]["conceded"],
            efficiency=round(
                goalkeeper_totals[player_id]["conceded"] / goalkeeper_totals[player_id]["played"],
                2,
            ),
            active=goalkeeper_players[player_id].active,
        )
        for rank, player_id in enumerate(eligible[:limit], start=1)
    ]

    return AllTimeRecords(
        goals=top("goals"),
        assists=top("assists"),
        played=top("played"),
        goalkeepers=goalkeepers,
    )
