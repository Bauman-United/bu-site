import json
from collections.abc import Callable

from bu_worker.dto import JoinFootballBundle
from bu_worker.http import PoliteClient
from bu_worker.sources.ingame.parse import parse_bundle, roster_for_season, season_ids


def fetch_bundles(
    client: PoliteClient,
    team_id: str,
    public_base: str,
    api_base: str,
    snapshot: Callable[[str, str], None],
    skip_seasons: set[str] | None = None,
) -> list[JoinFootballBundle]:
    team_raw = client.get(f"/teams/{team_id}/all")
    matches_raw = client.post(f"/teams/{team_id}/matches/v2", {})
    snapshot("team", team_raw)
    snapshot("matches", matches_raw)
    team = json.loads(team_raw)
    matches = json.loads(matches_raw)

    bundles = []
    for season_id in season_ids(matches):
        if season_id in (skip_seasons or set()):
            continue
        leaders_raw = client.post(
            f"/teams/{team_id}/bestPlayers",
            {"event_id": 1, "season_id": int(season_id)},
        )
        snapshot(f"season_{season_id}_leaders", leaders_raw)
        leaders = json.loads(leaders_raw)
        extra_players = {}
        for group in leaders.get("players", []):
            for player in group.get("players", []):
                extra_players[str(player["player_id"])] = {
                    **player,
                    "id": player["player_id"],
                }

        stats = {}
        roster = {str(player["id"]): player for player in roster_for_season(team, season_id)}
        player_rows = {**extra_players, **roster}
        for player in player_rows.values():
            player_id = str(player["id"])
            raw = client.post(
                f"/players/{player_id}/statistics",
                {"season_id": int(season_id), "team_id": int(team_id)},
            )
            snapshot(f"season_{season_id}_player_{player_id}", raw)
            stats[player_id] = json.loads(raw)
        bundles.append(
            parse_bundle(
                team,
                matches,
                stats,
                season_id,
                team_id,
                public_base,
                api_base,
                list(extra_players.values()),
            )
        )
    return bundles
