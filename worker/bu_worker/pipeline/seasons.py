"""Разовый перевод сезонов «2026-27» на календарные годы «2026».

Запуск: `python -m bu_worker migrate-seasons`.

Идемпотентно: турниры, уже лежащие в сезоне своего года, не трогаются.
"""

import re

from bu_core.models import Match, Season, Tournament
from bu_core.recompute import recompute
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from bu_worker.pipeline.common import ensure_season

_YEAR = re.compile(r"(?:19|20)\d{2}")


def tournament_year(session: Session, tournament: Tournament) -> str:
    """Год начала турнира: самый ранний матч, иначе год в названии («Весна 2026»,
    «ВЛ-2026»), иначе первый год старого сезона («2025-26» → 2025)."""
    first = session.scalar(
        select(func.min(Match.kickoff)).where(Match.tournament_id == tournament.id)
    )
    if first is not None:
        return str(first.year)
    years = _YEAR.findall(tournament.name)
    if years:
        return min(years)
    return tournament.season.slug[:4]


def migrate_seasons(session: Session) -> dict[str, int]:
    report = {"tournaments_moved": 0, "matches_moved": 0, "seasons_deleted": 0}
    for tournament in session.scalars(select(Tournament).order_by(Tournament.id)).all():
        old = tournament.season
        season = ensure_season(session, tournament_year(session, tournament))
        if season.final_place is None and old.final_place is not None:
            season.final_place = old.final_place
        if tournament.season_id != season.id:
            tournament.season_id = season.id
            report["tournaments_moved"] += 1
        moved = session.execute(
            update(Match)
            .where(Match.tournament_id == tournament.id, Match.season_id != season.id)
            .values(season_id=season.id)
            .execution_options(synchronize_session=False)
        )
        report["matches_moved"] += moved.rowcount  # type: ignore[attr-defined]
    session.flush()
    session.expire_all()

    used = select(Tournament.season_id).union(select(Match.season_id))
    for season in session.scalars(select(Season).where(Season.id.not_in(used))).all():
        session.delete(season)  # PlayerSeasonStats удалятся каскадом и пересчитаются
        report["seasons_deleted"] += 1
    session.flush()
    recompute(session)
    return report
