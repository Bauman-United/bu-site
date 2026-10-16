from collections import defaultdict
from typing import Any

from bu_core.models import Computed, Match, Player, PlayerSeasonStats, Season
from bu_core.stats import StatLine, leaders
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, full_name

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
        StatLine(pid, players[pid].slug, full_name(players[pid]), **v) for pid, v in sums.items()
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
