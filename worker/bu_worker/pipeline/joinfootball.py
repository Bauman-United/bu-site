from datetime import UTC, datetime

from bu_core.matching import AmbiguousMatchError, PlayerIndex, PlayerName
from bu_core.models import (
    IngestRun,
    Match,
    MatchEvent,
    Player,
    PlayerSourceLink,
    PlayerTournamentStats,
    StandingRow,
    Tournament,
)
from bu_core.text import player_slug, slugify, split_last_first
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bu_worker.dto import CalendarEntry, JoinFootballBundle, ParsedPlayer
from bu_worker.pipeline.common import (
    IngestResult,
    ensure_season,
    player_index,
    season_slug_for,
    unique_slug,
)

SOURCE = "joinfootball"
MIN_RATIO = 0.5


class SanityError(Exception):
    pass


def _counts(bundle: JoinFootballBundle) -> dict[str, int]:
    return {
        "players": len(bundle.players),
        "matches": len(bundle.calendar),
        "standings": len(bundle.standings),
    }


def sanity_check(session: Session, source_key: str, bundle: JoinFootballBundle) -> None:
    new = _counts(bundle)
    previous = session.scalars(
        select(IngestRun)
        .where(IngestRun.source == source_key, IngestRun.status == "ok")
        .order_by(IngestRun.started_at.desc())
        .limit(1)
    ).one_or_none()
    for key, value in new.items():
        if value == 0:
            raise SanityError(f"{key}: source returned 0 items")
        before = (previous.counts or {}).get(key, 0) if previous else 0
        # таблица турнира не может «похудеть» — любые потерянные строки = сломанная вёрстка
        limit = before if key == "standings" else before * MIN_RATIO
        if before and value < limit:
            raise SanityError(f"{key}: dropped from {before} to {value}")


def _upsert_tournament(session: Session, bundle: JoinFootballBundle) -> Tournament:
    info = bundle.tournament
    season = ensure_season(session, season_slug_for(info.period_start))
    tournament = session.scalars(
        select(Tournament).where(
            Tournament.source == SOURCE, Tournament.external_id == info.external_id
        )
    ).one_or_none()
    if tournament is None:
        tournament = Tournament(
            source=SOURCE,
            external_id=info.external_id,
            slug=unique_slug(session, Tournament, slugify(info.name)),
            short=info.name.split(" · ")[0],
            kind="league",
        )
        session.add(tournament)
    tournament.name = info.name
    tournament.url = info.url
    tournament.season_id = season.id
    session.flush()
    return tournament


def _resolve_player(
    session: Session, index: PlayerIndex, parsed: ParsedPlayer, warnings: list[str]
) -> Player | None:
    link = session.scalars(
        select(PlayerSourceLink).where(
            PlayerSourceLink.source == SOURCE,
            PlayerSourceLink.external_id == parsed.external_id,
        )
    ).one_or_none()
    if link is not None:
        return session.get(Player, link.player_id)
    try:
        player_id = index.find(parsed.full_name)
    except AmbiguousMatchError as exc:
        warnings.append(str(exc))
        return None
    if player_id is not None:
        other = session.scalars(
            select(PlayerSourceLink).where(
                PlayerSourceLink.player_id == player_id, PlayerSourceLink.source == SOURCE
            )
        ).first()
        if other is not None:  # тёзка: у найденного игрока уже другой id в источнике
            warnings.append(
                f"namesake {parsed.full_name!r} (id {parsed.external_id}) vs id "
                f"{other.external_id}: add an alias in content/players to split them"
            )
            return None
        player = session.get(Player, player_id)
    else:
        first, last = split_last_first(parsed.full_name)
        player = Player(
            first_name=first,
            last_name=last,
            slug=unique_slug(session, Player, player_slug(first, last)),
            aliases=[],
            manual_fields=[],
            achievements=[],
        )
        session.add(player)
        session.flush()
        index.add(PlayerName(player.id, first, last))
    session.add(
        PlayerSourceLink(
            player_id=player.id,
            source=SOURCE,
            external_id=parsed.external_id,
            external_name=parsed.full_name,
        )
    )
    return player


def _ingest_players(
    session: Session, bundle: JoinFootballBundle, tournament: Tournament, result: IngestResult
) -> PlayerIndex:
    index = player_index(session)
    present: set[int] = set()
    for parsed in bundle.players:
        player = _resolve_player(session, index, parsed, result.warnings)
        if player is None:
            continue
        present.add(player.id)
        manual = set(player.manual_fields or [])
        if "number" not in manual:
            player.number = parsed.number
        if "position" not in manual and parsed.position:
            player.position = parsed.position
        if "active" not in manual:
            player.active = True
        stats = session.get(PlayerTournamentStats, (player.id, tournament.id))
        if stats is None:
            stats = PlayerTournamentStats(player_id=player.id, tournament_id=tournament.id)
            session.add(stats)
        stats.played, stats.goals, stats.assists = parsed.played, parsed.goals, parsed.assists
        stats.yellow, stats.red = parsed.yellow, parsed.red
        result.tags.add(f"player:{player.slug}")
    session.flush()
    departed = session.scalars(
        select(Player)
        .join(PlayerTournamentStats, PlayerTournamentStats.player_id == Player.id)
        .where(PlayerTournamentStats.tournament_id == tournament.id, Player.id.not_in(present))
    )
    for player in departed:  # отзаявлен из турнира
        if "active" not in (player.manual_fields or []):
            player.active = False
            result.tags.add(f"player:{player.slug}")
    session.flush()
    return index


def _find_in_index(index: PlayerIndex, name: str | None, warnings: list[str]) -> int | None:
    if not name:
        return None
    try:
        return index.find(name)
    except AmbiguousMatchError as exc:
        warnings.append(str(exc))
        return None


def _ingest_match(
    session: Session,
    entry: CalendarEntry,
    bundle: JoinFootballBundle,
    tournament: Tournament,
    our_team_id: str,
    index: PlayerIndex,
    result: IngestResult,
) -> None:
    home = entry.home_team_id == our_team_id
    opponent = entry.away_name if home else entry.home_name
    match = session.scalars(
        select(Match).where(Match.source == SOURCE, Match.external_id == entry.external_id)
    ).one_or_none()
    if match is None:
        base = f"{entry.kickoff.date().isoformat()}-{slugify(opponent)}"
        match = Match(
            source=SOURCE, external_id=entry.external_id, slug=unique_slug(session, Match, base)
        )
        session.add(match)
    match.tournament_id = tournament.id
    match.season_id = tournament.season_id
    match.round = entry.round
    match.kickoff = entry.kickoff
    match.home = home
    match.venue_name = entry.venue_name
    match.venue_address = entry.venue_address
    match.opponent_name = opponent
    match.opponent_logo = entry.away_logo if home else entry.home_logo
    match.source_url = f"{bundle.tournament.url.split('/tournament/')[0]}/match/{entry.external_id}"
    finished = entry.home_score is not None and entry.away_score is not None
    if finished:
        match.score_us = entry.home_score if home else entry.away_score
        match.score_them = entry.away_score if home else entry.home_score
        match.status = "finished"
    else:
        match.score_us = match.score_them = None
        match.status = match.status if match.status in {"live", "cancelled"} else "scheduled"

    detail = bundle.details.get(entry.external_id)
    manual = set(match.manual_fields or [])
    our_side = "home" if home else "away"
    # пустой разбор не затирает уже известные события; ручные события из content/ важнее
    if detail is not None and detail.events and "events" not in manual:
        match.events.clear()
        session.flush()
        for ev in detail.events:
            is_us = ev.side == our_side
            match.events.append(
                MatchEvent(
                    minute=ev.minute,
                    type=ev.type,
                    team="us" if is_us else "them",
                    player_name=ev.player_name,
                    assist_name=ev.assist_name,
                    note=ev.note,
                    player_id=_find_in_index(index, ev.player_name, result.warnings)
                    if is_us
                    else None,
                    assist_id=_find_in_index(index, ev.assist_name, result.warnings)
                    if is_us
                    else None,
                )
            )
    if detail is not None and detail.mvp_name and "mvp" not in manual:
        match.mvp_player_id = (
            _find_in_index(index, detail.mvp_name, result.warnings)
            if detail.mvp_side == our_side
            else None
        )
    session.flush()
    result.tags.add(f"match:{match.slug}")


def _ingest_standings(
    session: Session, bundle: JoinFootballBundle, tournament: Tournament, our_names: list[str]
) -> None:
    session.execute(delete(StandingRow).where(StandingRow.tournament_id == tournament.id))
    now = datetime.now(UTC)
    names = {n.lower() for n in our_names}
    for row in bundle.standings:
        session.add(
            StandingRow(
                tournament_id=tournament.id,
                updated_at=now,
                is_us=row.team_name.lower() in names,
                **row.model_dump(),
            )
        )
    session.flush()


def ingest(
    session: Session, bundle: JoinFootballBundle, our_team_id: str, our_names: list[str]
) -> IngestResult:
    result = IngestResult(counts=_counts(bundle))
    tournament = _upsert_tournament(session, bundle)
    index = _ingest_players(session, bundle, tournament, result)
    for entry in bundle.calendar:
        _ingest_match(session, entry, bundle, tournament, our_team_id, index, result)
    _ingest_standings(session, bundle, tournament, our_names)
    result.tags |= {"matches", "players", "standings", "home", "stats"}
    return result
