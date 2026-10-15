from datetime import datetime
from typing import Any

from bu_core.models import ContentDoc, Season, StandingRow, Tournament
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, tournament_out
from bu_api.schemas import TournamentOut

router = APIRouter()


class SeasonOut(BaseModel):
    slug: str
    label: str
    final_place: str | None


class StandingRowOut(BaseModel):
    pos: int
    team_name: str
    team_logo: str | None
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    pts: int
    is_us: bool


class StandingsOut(BaseModel):
    tournament: TournamentOut
    updated_at: datetime | None
    source_url: str | None
    rows: list[StandingRowOut]


@router.get("/club")
def club(session: Session = Depends(get_session)) -> dict[str, Any]:
    doc = session.get(ContentDoc, "club")
    if doc is None:
        raise HTTPException(404, "club content not synced")
    return doc.data


@router.get("/history")
def history(session: Session = Depends(get_session)) -> dict[str, Any]:
    doc = session.get(ContentDoc, "history")
    base: dict[str, Any] = {"timeline": [], "trophies": [], "legends": []}
    return {**base, **(doc.data if doc else {})}


@router.get("/seasons")
def seasons(session: Session = Depends(get_session)) -> list[SeasonOut]:
    rows = session.scalars(select(Season).order_by(Season.slug.desc()))
    return [SeasonOut(slug=s.slug, label=s.label, final_place=s.final_place) for s in rows]


def _tournaments(session: Session, season: str | None) -> list[Tournament]:
    query = select(Tournament).join(Season).order_by(Tournament.name)
    if season:
        query = query.where(Season.slug == season)
    return list(session.scalars(query))


@router.get("/tournaments")
def tournaments(
    season: str | None = None, session: Session = Depends(get_session)
) -> list[TournamentOut]:
    return [tournament_out(t) for t in _tournaments(session, season)]


@router.get("/standings")
def standings(
    tournament: str | None = None, session: Session = Depends(get_session)
) -> list[StandingsOut]:
    if tournament:
        selected = list(session.scalars(select(Tournament).where(Tournament.slug == tournament)))
    else:
        selected = _tournaments(session, current_season(session))
    out = []
    for t in selected:
        rows = list(
            session.scalars(
                select(StandingRow)
                .where(StandingRow.tournament_id == t.id)
                .order_by(StandingRow.pos)
            )
        )
        if not rows:
            continue
        out.append(
            StandingsOut(
                tournament=tournament_out(t),
                updated_at=max(r.updated_at for r in rows),
                source_url=f"{t.url}/tables" if t.url else None,
                rows=[StandingRowOut.model_validate(r, from_attributes=True) for r in rows],
            )
        )
    return out
