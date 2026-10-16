from collections.abc import Callable

from bu_worker.dto import JoinFootballBundle, MatchDetail
from bu_worker.http import PoliteClient
from bu_worker.sources.lfl.parse import (
    ParseError,
    parse_calendar,
    parse_current_player_ids,
    parse_match,
    parse_players,
    parse_season_id,
    parse_standings,
    parse_tournament_info,
)


def fetch_bundle(
    client: PoliteClient,
    tournament_id: str,
    club_id: str,
    base_url: str,
    snapshot: Callable[[str, str], None],
) -> JoinFootballBundle:
    def get(name: str, path: str) -> str:
        html = client.get(path)
        snapshot(name, html)
        return html

    tournament_url = f"{base_url}/tournament{tournament_id}"
    tournament_html = get("tournament", f"/tournament{tournament_id}")
    season_id = parse_season_id(tournament_html)
    current_player_ids = parse_current_player_ids(get("club", f"/club{club_id}"))
    calendar = parse_calendar(
        get(
            "calendar",
            f"/club{club_id}/calendar?matches=all&sort=timeasc&season_id={season_id}",
        ),
        tournament_id,
    )
    players = parse_players(
        get(
            "squad",
            "/?ajax=1&method=tournament_squads_table"
            f"&tournament_id={tournament_id}&club_id={club_id}",
        ),
        current_player_ids,
    )
    details: dict[str, MatchDetail] = {}
    for entry in calendar:
        if entry.home_score is not None:
            details[entry.external_id] = parse_match(
                get(f"match_{entry.external_id}", f"/match{entry.external_id}")
            )
    tournament = parse_tournament_info(tournament_html, tournament_id, tournament_url)
    try:
        standings = parse_standings(tournament_html)
    except ParseError:
        if "кубок" not in tournament.name.lower():
            raise
        standings = []
    return JoinFootballBundle(
        tournament=tournament,
        players=players,
        calendar=calendar,
        details=details,
        standings=standings,
    )
