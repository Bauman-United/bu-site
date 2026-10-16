from bu_core.models import (
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    News,
    Player,
    Tournament,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bu_worker.pipeline.common import IngestResult, ensure_season, player_index
from bu_worker.sources.content import ContentBundle, MatchContent, PlayerContent


def _set_doc(session: Session, key: str, data: dict) -> None:
    doc = session.get(ContentDoc, key)
    if doc is None:
        session.add(ContentDoc(key=key, data=data))
    else:
        doc.data = data


def _sync_player(session: Session, slug: str, content: PlayerContent) -> Player:
    player = session.scalars(select(Player).where(Player.slug == slug)).one_or_none()
    if player is None and content.first_name and content.last_name:
        player_id = player_index(session).find(f"{content.last_name} {content.first_name}")
        player = session.get(Player, player_id) if player_id else None
    if player is None:
        player = Player(
            slug=slug,
            first_name=content.first_name or "",
            last_name=content.last_name or slug,
            aliases=[],
            manual_fields=[],
            achievements=[],
        )
        session.add(player)
    if content.first_name:
        player.first_name = content.first_name
    if content.last_name:
        player.last_name = content.last_name
    player.aliases = list(content.aliases)
    provided = content.provided_fields()
    for field in provided:
        value = getattr(content, field)
        if field == "achievements":
            value = [a.model_dump() for a in value or []]
        setattr(player, field, value)
    player.manual_fields = sorted(provided)
    session.flush()
    return player


def _player_id_by_slug(session: Session, slug: str | None) -> int | None:
    if not slug:
        return None
    return session.scalars(select(Player.id).where(Player.slug == slug)).one_or_none()


def _events(session: Session, content: MatchContent) -> list[MatchEvent]:
    events = []
    for ev in content.events:
        is_us = ev.team == "us"
        events.append(
            MatchEvent(
                minute=ev.minute,
                type=ev.type,
                team=ev.team,
                note=ev.note,
                player_id=_player_id_by_slug(session, ev.player) if is_us else None,
                player_name=None if is_us else ev.player,
                assist_id=_player_id_by_slug(session, ev.assist) if is_us else None,
                assist_name=None if is_us else ev.assist,
            )
        )
    return events


def _sync_match(session: Session, slug: str, content: MatchContent, result: IngestResult) -> None:
    match = session.scalars(select(Match).where(Match.slug == slug)).one_or_none()
    if match is None:
        missing = [
            f
            for f in ("tournament", "kickoff", "home", "opponent", "status")
            if getattr(content, f) is None
        ]
        if missing:
            result.warnings.append(f"matches/{slug}.yaml: new match needs {', '.join(missing)}")
            return
        tournament = session.scalars(
            select(Tournament).where(Tournament.slug == content.tournament)
        ).one_or_none()
        if tournament is None:
            result.warnings.append(f"matches/{slug}.yaml: unknown tournament {content.tournament}")
            return
        match = Match(
            slug=slug, source="manual", tournament_id=tournament.id, season_id=tournament.season_id
        )
        session.add(match)
    if match.source == "manual":
        match.round = content.round
        if content.kickoff is not None:
            match.kickoff = content.kickoff
        match.home = bool(content.home)
        match.venue_name = content.venue.name if content.venue else None
        match.venue_address = content.venue.address if content.venue else None
        match.opponent_name = content.opponent.name if content.opponent else ""
        match.opponent_logo = content.opponent.logo if content.opponent else None
        match.status = content.status or "scheduled"
        match.score_us = content.score.us if content.score else None
        match.score_them = content.score.them if content.score else None
    session.flush()
    manual = set(match.manual_fields or [])
    if match.source != "manual":  # матч из источника: дату/место можно задать вручную
        if content.kickoff is not None:
            match.kickoff = content.kickoff
            manual.add("kickoff")
        if content.venue is not None:
            match.venue_name = content.venue.name
            match.venue_address = content.venue.address
            manual.add("venue")
    if content.events:  # события из content/ важнее спарсенных, парсер их больше не трогает
        match.events.clear()
        session.flush()
        match.events.extend(_events(session, content))
        manual.add("events")
    if content.mvp:
        match.mvp_player_id = _player_id_by_slug(session, content.mvp)
        manual.add("mvp")
    match.manual_fields = sorted(manual)
    match.report_news_slug = content.report_news or match.report_news_slug
    match.stream_url = content.stream_url or match.stream_url
    match.video_url = content.video_url or match.video_url
    if content.squad:
        session.execute(delete(MatchAppearance).where(MatchAppearance.match_id == match.id))
        for player_slug in content.squad:
            player_id = _player_id_by_slug(session, player_slug)
            if player_id is None:
                result.warnings.append(f"matches/{slug}.yaml: unknown player {player_slug}")
                continue
            session.add(MatchAppearance(match_id=match.id, player_id=player_id))
    session.flush()
    result.tags.add(f"match:{slug}")


def sync_content(session: Session, bundle: ContentBundle) -> IngestResult:
    result = IngestResult()
    _set_doc(session, "club", bundle.club)
    _set_doc(session, "history", bundle.history)

    for t in bundle.tournaments:
        season = ensure_season(session, t.season)
        tournament = session.scalars(
            select(Tournament).where(Tournament.slug == t.slug)
        ).one_or_none()
        if tournament is None:
            tournament = Tournament(slug=t.slug, source="manual")
            session.add(tournament)
        tournament.name, tournament.short, tournament.kind = t.name, t.short, t.kind
        tournament.url, tournament.season_id = t.url, season.id
    session.flush()

    for slug, content in bundle.players.items():
        player = _sync_player(session, slug, content)
        result.tags.add(f"player:{player.slug}")

    keep = {n.slug for n in bundle.news}
    removed = session.scalars(
        select(News.slug).where(News.origin == "content", News.slug.not_in(keep))
    ).all()
    result.tags |= {f"news:{slug}" for slug in removed}
    session.execute(delete(News).where(News.origin == "content", News.slug.not_in(keep)))
    for n in bundle.news:
        news = session.scalars(select(News).where(News.slug == n.slug)).one_or_none()
        if news is None:
            news = News(slug=n.slug)
            session.add(news)
        news.date, news.tag, news.title, news.lead = n.date, n.tag, n.title, n.lead
        news.body_md, news.cover, news.featured = n.body, n.cover, n.featured
        news.match_slug = n.match
        news.source_platform = n.source.platform if n.source else None
        news.source_url = n.source.url if n.source else None
        result.tags.add(f"news:{n.slug}")
    session.flush()

    for slug, match_content in bundle.matches.items():
        _sync_match(session, slug, match_content, result)

    result.counts = {
        "players": len(bundle.players),
        "news": len(bundle.news),
        "matches": len(bundle.matches),
    }
    result.tags |= {"club", "history", "news", "players", "matches", "home", "stats"}
    return result
