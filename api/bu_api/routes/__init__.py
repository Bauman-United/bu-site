from zoneinfo import ZoneInfo

from bu_core.models import Computed, Match, News, Player, Tournament
from bu_core.stats import outcome
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.schemas import MatchSummary, NewsCard, TournamentOut

MSK = ZoneInfo("Europe/Moscow")


def current_season(session: Session) -> str | None:
    meta = session.get(Computed, "meta")
    return meta.data.get("current_season") if meta else None


def tournament_out(t: Tournament) -> TournamentOut:
    return TournamentOut(
        slug=t.slug, name=t.name, short=t.short, kind=t.kind, season=t.season.slug, url=t.url
    )


def match_summary(m: Match) -> MatchSummary:
    finished = m.status == "finished" and m.score_us is not None and m.score_them is not None
    return MatchSummary(
        slug=m.slug,
        kickoff=m.kickoff.astimezone(MSK),
        tournament=tournament_out(m.tournament),
        round=m.round,
        home=m.home,
        venue_name=m.venue_name,
        venue_address=m.venue_address,
        opponent_name=m.opponent_name,
        opponent_logo=m.opponent_logo,
        status=m.status,
        score_us=m.score_us,
        score_them=m.score_them,
        outcome=outcome(m.score_us, m.score_them) if finished else None,  # type: ignore[arg-type]
        stream_url=m.stream_url,
        source_url=m.source_url,
    )


def news_card(n: News) -> NewsCard:
    return NewsCard(
        slug=n.slug,
        date=n.date,
        tag=n.tag,
        title=n.title,
        lead=n.lead,
        cover=n.cover,
        source_platform=n.source_platform,
        source_url=n.source_url,
        match_slug=n.match_slug,
        featured=n.featured,
    )


def full_name(p: Player) -> str:
    return f"{p.first_name} {p.last_name}".strip()


def players_by_id(session: Session, ids: set[int]) -> dict[int, Player]:
    if not ids:
        return {}
    return {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(ids)))}
