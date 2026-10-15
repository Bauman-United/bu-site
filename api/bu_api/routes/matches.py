from typing import Literal

from bu_core.models import Match, News, Player, Season, Tournament
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import full_name, match_summary, news_card, players_by_id
from bu_api.schemas import EventOut, MatchDetail, MatchSummary, PlayerRef

router = APIRouter()


def _surname(name: str | None) -> str:
    return (name or "").split()[0] if name else "—"


@router.get("/matches")
def list_matches(
    season: str | None = None,
    tournament: str | None = None,
    where: Literal["home", "away"] | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
) -> list[MatchSummary]:
    query = select(Match).join(Tournament).order_by(Match.kickoff)
    if season:
        query = query.join(Season, Season.id == Match.season_id).where(Season.slug == season)
    if tournament:
        query = query.where(Tournament.slug == tournament)
    if where:
        query = query.where(Match.home.is_(where == "home"))
    if status:
        query = query.where(Match.status == status)
    return [match_summary(m) for m in session.scalars(query)]


@router.get("/matches/{slug}")
def match_detail(slug: str, session: Session = Depends(get_session)) -> MatchDetail:
    m = session.scalars(select(Match).where(Match.slug == slug)).one_or_none()
    if m is None:
        raise HTTPException(404, "match not found")
    ids = {i for e in m.events for i in (e.player_id, e.assist_id) if i}
    if m.mvp_player_id:
        ids.add(m.mvp_player_id)
    people = players_by_id(session, ids)

    def ref(pid: int | None) -> Player | None:
        return people.get(pid) if pid else None

    events = []
    scorers_us: list[str] = []
    scorers_them: list[str] = []
    for e in m.events:
        player, assist = ref(e.player_id), ref(e.assist_id)
        events.append(
            EventOut(
                minute=e.minute,
                type=e.type,
                team=e.team,
                player_slug=player.slug if player else None,
                player_name=full_name(player) if player else e.player_name,
                assist_slug=assist.slug if assist else None,
                assist_name=full_name(assist) if assist else e.assist_name,
                note=e.note,
            )
        )
        if e.type in ("goal", "penalty", "own_goal"):
            scorer = player.last_name if player else _surname(e.player_name)
            label = f"{scorer} {e.minute}'" + (" (аг)" if e.type == "own_goal" else "")
            (scorers_us if e.team == "us" else scorers_them).append(label)

    report = None
    if m.report_news_slug:
        news = session.scalars(select(News).where(News.slug == m.report_news_slug)).one_or_none()
        report = news_card(news) if news else None
    if report is None:
        news = session.scalars(select(News).where(News.match_slug == m.slug)).first()
        report = news_card(news) if news else None

    ordered = list(session.scalars(select(Match.slug).order_by(Match.kickoff)))
    i = ordered.index(m.slug)
    mvp = ref(m.mvp_player_id)
    return MatchDetail(
        **match_summary(m).model_dump(),
        events=events,
        scorers_us=scorers_us,
        scorers_them=scorers_them,
        mvp=PlayerRef(slug=mvp.slug, name=full_name(mvp), number=mvp.number) if mvp else None,
        report=report,
        video_url=m.video_url,
        prev_slug=ordered[i - 1] if i > 0 else None,
        next_slug=ordered[i + 1] if i + 1 < len(ordered) else None,
    )
