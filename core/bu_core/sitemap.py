"""Адреса сайта и даты их изменения: общий источник для sitemap.xml (API) и IndexNow (воркер)."""

from datetime import date, datetime

from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session

from bu_core.models import (
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    News,
    Player,
    StandingRow,
)

STATIC = [
    "/",
    "/matches",
    "/standings",
    "/team",
    "/hall-of-fame",
    "/news",
    "/about",
    "/join",
    "/partners",
]


def _latest(*values: date | datetime | None) -> date | None:
    days = [v.date() if isinstance(v, datetime) else v for v in values if v is not None]
    return max(days, default=None)


def sitemap_entries(session: Session) -> list[tuple[str, date | None]]:
    """(путь, lastmod). lastmod — реальная дата изменения данных страницы, а не «сегодня»:
    поисковики перестают верить lastmod, если он меняется без изменений на странице."""
    matches = session.scalar(select(func.max(Match.updated_at)))
    news = session.scalar(select(func.max(News.date)))
    standings = session.scalar(select(func.max(StandingRow.updated_at)))
    content = session.scalar(select(func.max(ContentDoc.updated_at)))
    static_lastmod = {
        "/": _latest(matches, news, content),
        "/matches": _latest(matches),
        "/standings": _latest(standings, matches),
        "/team": _latest(matches, content),
        "/hall-of-fame": _latest(matches, content),
        "/news": _latest(news),
        "/about": _latest(content),
        "/join": _latest(content),
        "/partners": _latest(content),
    }
    entries: list[tuple[str, date | None]] = [(p, static_lastmod[p]) for p in STATIC]
    for m in session.scalars(select(Match)):
        entries.append((f"/matches/{m.slug}", _latest(m.updated_at)))
    # Страница игрока меняется вместе с матчами, где он вышел на поле, забил или отдал передачу.
    involved = union_all(
        select(MatchAppearance.player_id.label("player_id"), MatchAppearance.match_id),
        select(MatchEvent.player_id, MatchEvent.match_id).where(MatchEvent.player_id.is_not(None)),
        select(MatchEvent.assist_id, MatchEvent.match_id).where(MatchEvent.assist_id.is_not(None)),
    ).subquery()
    player_lastmod: dict[int, datetime] = dict(
        session.execute(
            select(involved.c.player_id, func.max(Match.updated_at))
            .join(Match, Match.id == involved.c.match_id)
            .group_by(involved.c.player_id)
        ).all()
    )
    for p in session.scalars(select(Player)):
        entries.append((f"/team/{p.slug}", _latest(player_lastmod.get(p.id))))
    for n in session.scalars(select(News)):
        entries.append((f"/news/{n.slug}", n.date))
    return entries
