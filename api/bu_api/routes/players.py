from collections.abc import Mapping
from types import SimpleNamespace
from typing import Literal

from bu_core.models import Player, PlayerSeasonStats, PlayerTournamentStats, Season, Tournament
from bu_core.recompute import tournament_lines
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, tournament_out
from bu_api.schemas import (
    PlayerCard,
    PlayerDetail,
    PlayerStats,
    SeasonRow,
    TournamentStatsRow,
)

router = APIRouter()
POSITION_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}
STAT_KEYS = ("played", "goals", "assists", "yellow", "red", "mvp")
# ?league= → Tournament.source: БЛ — Бауманская лига (join.football), ЛФЛ — lfl.ru
LEAGUE_SOURCES = {"bl": "joinfootball", "lfl": "lfl"}


def _league_rows(session: Session, league: str, season: str | None) -> dict[int, SimpleNamespace]:
    """Суммы по всем турнирам лиги (вкл. кубки) текущего сезона, по игроку."""
    if not season:
        return {}
    rows = session.scalars(
        select(PlayerTournamentStats)
        .join(Tournament)
        .join(Season, Season.id == Tournament.season_id)
        .where(Season.slug == season, Tournament.source == LEAGUE_SOURCES[league])
    )
    totals: dict[int, SimpleNamespace] = {}
    for r in rows:
        acc = totals.setdefault(r.player_id, SimpleNamespace(**dict.fromkeys(STAT_KEYS, 0)))
        for k in STAT_KEYS:
            setattr(acc, k, getattr(acc, k) + (getattr(r, k, 0) or 0))
    return totals


def _stats(row: PlayerSeasonStats | PlayerTournamentStats | SimpleNamespace | None) -> PlayerStats:
    if row is None:
        return PlayerStats()
    return PlayerStats(**{k: getattr(row, k, 0) for k in STAT_KEYS})


def _season_rows(session: Session, slug: str | None) -> dict[int, PlayerSeasonStats]:
    if not slug:
        return {}
    rows = session.scalars(select(PlayerSeasonStats).join(Season).where(Season.slug == slug))
    return {r.player_id: r for r in rows}


def _tournament_rows(session: Session, slug: str) -> dict[int, PlayerTournamentStats]:
    rows = session.scalars(
        select(PlayerTournamentStats).join(Tournament).where(Tournament.slug == slug)
    )
    return {r.player_id: r for r in rows}


def _sorted(players: list[Player]) -> list[Player]:
    return sorted(
        players,
        key=lambda p: (
            POSITION_ORDER.get(p.position or "", 9),
            p.number if p.number is not None else 999,
            p.last_name,
        ),
    )


def _card(p: Player, stats: PlayerStats) -> dict:
    return dict(
        slug=p.slug,
        first_name=p.first_name,
        last_name=p.last_name,
        number=p.number,
        position=p.position,
        nickname=p.nickname,
        photo=p.photo,
        is_captain=p.is_captain,
        season=stats,
    )


@router.get("/players")
def list_players(
    active: bool | None = None,
    tournament: str | None = None,
    league: Literal["bl", "lfl"] | None = None,
    roster: bool = False,
    session: Session = Depends(get_session),
) -> list[PlayerCard]:
    """`roster=true` — общий состав: текущая заявка плюс все, кто играл в сезоне/турнире.

    `league=bl|lfl` — суммы по всем турнирам лиги текущего сезона (вместе с кубками).
    """
    query = select(Player)
    stats: Mapping[int, PlayerSeasonStats | PlayerTournamentStats | SimpleNamespace]
    if tournament or league:
        stats = (
            _tournament_rows(session, tournament)
            if tournament
            else _league_rows(session, league or "", current_season(session))
        )
        if not stats:
            return []
        query = query.where(Player.id.in_(stats))
    else:
        stats = _season_rows(session, current_season(session))
    if roster:
        played = [pid for pid, row in stats.items() if row.played > 0]
        query = query.where(or_(Player.active.is_(True), Player.id.in_(played)))
    elif active is not None:
        query = query.where(Player.active.is_(active))
    return [
        PlayerCard(**_card(p, _stats(stats.get(p.id))))
        for p in _sorted(list(session.scalars(query)))
    ]


@router.get("/players/{slug}")
def player_detail(slug: str, session: Session = Depends(get_session)) -> PlayerDetail:
    p = session.scalars(select(Player).where(Player.slug == slug)).one_or_none()
    if p is None:
        raise HTTPException(404, "player not found")
    season_slug = current_season(session)
    team_rows = _season_rows(session, season_slug)
    history = session.execute(
        select(PlayerSeasonStats, Season)
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .where(PlayerSeasonStats.player_id == p.id)
        .order_by(Season.slug.desc())
    ).all()
    seasons = [SeasonRow(season=s.slug, label=s.label, stats=_stats(row)) for row, s in history]
    total = PlayerStats(**{k: sum(getattr(r.stats, k) for r in seasons) for k in STAT_KEYS})
    mine = team_rows.get(p.id)
    team_best = [
        k
        for k in ("goals", "assists", "mvp", "played")
        if mine is not None
        and getattr(mine, k) > 0
        and getattr(mine, k) == max(getattr(r, k) for r in team_rows.values())
    ]
    roster = [
        x.slug
        for x in _sorted(list(session.scalars(select(Player).where(Player.active.is_(True)))))
    ]
    i = roster.index(p.slug) if p.slug in roster else -1
    per_tournament = tournament_lines(session, p.id)
    tournaments = {
        t.id: t
        for t in session.scalars(
            select(Tournament).where(Tournament.id.in_([tid for _, tid in per_tournament]))
        )
    }
    by_tournament = sorted(
        (
            TournamentStatsRow(
                tournament=tournament_out(tournaments[tid]),
                season=tournaments[tid].season.slug,
                stats=PlayerStats(**values),
            )
            for (_, tid), values in per_tournament.items()
        ),
        key=lambda r: (r.season, r.stats.played, r.tournament.name),
        reverse=True,
    )
    return PlayerDetail(
        **_card(p, _stats(mine)),
        role=p.role,
        foot=p.foot,
        faculty=p.faculty,
        joined=p.joined,
        fact=p.fact,
        achievements=p.achievements or [],
        seasons=seasons,
        tournaments=by_tournament,
        total=total,
        team_best=team_best,
        prev_slug=roster[i - 1] if i > 0 else None,
        next_slug=roster[i + 1] if 0 <= i < len(roster) - 1 else None,
    )
