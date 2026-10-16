from datetime import UTC, datetime, timedelta
from typing import Any

from bu_core.models import Computed, ContentDoc, Match, News, Player, Season, Tournament
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, full_name, match_summary, news_card
from bu_api.routes.catalog import standings
from bu_api.routes.matches import match_detail

router = APIRouter()
LIVE_WINDOW = timedelta(hours=2)
# (ключ блока, Tournament.source, подпись) — порядок блоков на главной
LEAGUES = (("bl", "joinfootball", "Бауманская лига"), ("lfl", "lfl", "ЛФЛ"))


def _around_us(table: Any, size: int = 5) -> Any:
    rows = table.rows
    us = next((i for i, r in enumerate(rows) if r.is_us), 0)
    start = max(0, min(us - size // 2, len(rows) - size))
    table.rows = rows[start : start + size]
    return table


def _league(
    session: Session, key: str, source: str, title: str, season: str | None
) -> dict[str, Any] | None:
    """Последний сыгранный матч и мини-таблица (5 строк вокруг нас) турниров одного источника."""
    last = session.scalars(
        select(Match)
        .join(Tournament, Match.tournament_id == Tournament.id)
        .where(Match.status == "finished", Tournament.source == source)
        .order_by(Match.kickoff.desc().nulls_last(), Match.id.desc())
    ).first()
    tables = []
    if season:
        slugs = session.scalars(
            select(Tournament.slug)
            .join(Season)
            .where(Season.slug == season, Tournament.source == source)
            .order_by(Tournament.name)
        )
        tables = [t for slug in slugs for t in standings(tournament=slug, session=session)]
    # несколько турниров источника в сезоне — берём таблицу, обновлённую последней
    table = max(tables, key=lambda t: t.updated_at or datetime.min.replace(tzinfo=UTC), default=None)
    if last is None and table is None:
        return None
    return {
        "league": key,
        "title": title,
        "last_match": match_detail(last.slug, session) if last else None,
        "standings": _around_us(table) if table else None,
    }


@router.get("/home")
def home(session: Session = Depends(get_session)) -> dict[str, Any]:
    now = datetime.now(UTC)
    upcoming = session.scalars(
        select(Match)
        .where(Match.status.in_(("scheduled", "live")), Match.kickoff >= now - LIVE_WINDOW)
        .order_by(Match.kickoff)
    ).first()
    if upcoming is None:  # датированных впереди нет — показываем матч с «Дата уточняется»
        upcoming = session.scalars(
            select(Match)
            .where(Match.status.in_(("scheduled", "live")), Match.kickoff.is_(None))
            .order_by(Match.id)
        ).first()
    last = session.scalars(
        select(Match).where(Match.status == "finished").order_by(Match.kickoff.desc().nulls_last())
    ).first()
    live = None
    if (
        upcoming
        and upcoming.stream_url
        and (
            upcoming.status == "live"
            or (
                upcoming.kickoff is not None
                and upcoming.kickoff <= now <= upcoming.kickoff + LIVE_WINDOW
            )
        )
    ):
        live = match_summary(upcoming)

    season = current_season(session)
    season_doc = session.get(Computed, f"season:{season}") if season else None
    season_data = season_doc.data if season_doc else {"form": [], "totals": {}, "leaders": {}}
    club_doc = session.get(ContentDoc, "club")
    club = club_doc.data if club_doc else {}
    computed_club = session.get(Computed, "club")

    tables = standings(tournament=club.get("primary_tournament"), session=session)
    leaders = season_data.get("leaders", {})
    pom = club.get("player_of_month")
    if pom and pom.get("player"):
        p = session.scalars(select(Player).where(Player.slug == pom["player"])).one_or_none()
        pom = {**pom, "slug": p.slug, "name": full_name(p), "photo": p.photo} if p else None

    by_league = [_league(session, *league, season) for league in LEAGUES]
    news = session.scalars(select(News).order_by(News.date.desc(), News.slug).limit(4))
    return {
        "next_match": match_summary(upcoming) if upcoming else None,
        "last_match": match_detail(last.slug, session) if last else None,
        "form": season_data.get("form", []),
        "totals": season_data.get("totals", {}),
        "standings": _around_us(tables[0]) if tables else None,
        "news": [news_card(n) for n in news],
        "leaders": {
            "goals": (leaders.get("goals") or [None])[0],
            "assists": (leaders.get("assists") or [None])[0],
            "player_of_month": pom,
        },
        "numbers": computed_club.data["numbers"] if computed_club else {},
        "live": live,
        "by_league": [b for b in by_league if b],
    }
