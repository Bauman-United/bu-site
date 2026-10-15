from dataclasses import dataclass, field
from datetime import date
from typing import Any

from bu_core.matching import PlayerIndex, PlayerName
from bu_core.models import Player, Season
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class IngestResult:
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)


def season_slug_for(d: date) -> str:
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def ensure_season(session: Session, slug: str) -> Season:
    season = session.scalars(select(Season).where(Season.slug == slug)).one_or_none()
    if season is None:
        start, end = slug.split("-")
        season = Season(slug=slug, label=f"{start}/{end}")
        session.add(season)
        session.flush()
    return season


def unique_slug(session: Session, model: Any, base: str, exclude_id: int | None = None) -> str:
    slug, n = base, 2
    while True:
        existing = session.scalars(select(model).where(model.slug == slug)).one_or_none()
        if existing is None or existing.id == exclude_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


def player_index(session: Session) -> PlayerIndex:
    return PlayerIndex(
        PlayerName(p.id, p.first_name, p.last_name, tuple(p.aliases or ()))
        for p in session.scalars(select(Player))
    )
