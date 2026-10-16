from collections.abc import Callable

from bu_worker.dto import JoinFootballBundle, MatchDetail
from bu_worker.http import PoliteClient
from bu_worker.sources.joinfootball.parse import (
    ParseError,
    parse_application,
    parse_calendar,
    parse_match,
    parse_standings,
    parse_tournament_info,
)


def fetch_bundle(
    client: PoliteClient,
    tournament_id: str,
    team_id: str,
    base_url: str,
    snapshot: Callable[[str, str], None],
) -> JoinFootballBundle:
    def get(name: str, path: str) -> str:
        html = client.get(path)
        snapshot(name, html)
        return html

    calendar_html = get("calendar", f"/tournament/{tournament_id}/calendar")
    info = parse_tournament_info(
        calendar_html, tournament_id, f"{base_url}/tournament/{tournament_id}"
    )
    calendar = [
        e
        for e in parse_calendar(calendar_html, info.period_start, info.period_end)
        if team_id in (e.home_team_id, e.away_team_id)
    ]
    players = parse_application(
        get("application", f"/tournament/{tournament_id}/teams/application?team_id={team_id}")
    )
    tables_html = get("tables", f"/tournament/{tournament_id}/tables")
    try:
        standings = parse_standings(tables_html)
    except ParseError:
        if "кубок" not in info.name.lower():
            raise
        standings = []  # у кубка вместо таблицы сетка плей-офф
    details: dict[str, MatchDetail] = {}
    for entry in calendar:
        if entry.home_score is not None:
            try:
                details[entry.external_id] = parse_match(
                    get(f"match_{entry.external_id}", f"/match/{entry.external_id}")
                )
            except ParseError:
                # Протокол не заполнен (часто в кубках) — матч берём без событий,
                # уже известные события ingest не затирает.
                continue
    return JoinFootballBundle(
        tournament=info, players=players, calendar=calendar, details=details, standings=standings
    )
