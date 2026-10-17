from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from bu_worker.dto import CalendarEntry, JoinFootballBundle, ParsedPlayer, TournamentInfo

MSK = ZoneInfo("Europe/Moscow")
POSITION = {
    "Вратарь": "GK",
    "Защитник": "DF",
    "Полузащитник": "MF",
    "Нападающий": "FW",
}


class ParseError(ValueError):
    pass


def _absolute_image(value: str | None, api_base: str) -> str | None:
    if not value:
        return None
    return (
        value
        if value.startswith(("http://", "https://"))
        else f"{api_base.rstrip('/')}/{value.lstrip('/')}"
    )


def season_ids(matches_data: Mapping[str, Any]) -> list[str]:
    ids = {str(row["season_id"]) for row in matches_data.get("matches", []) if row.get("season_id")}
    return sorted(ids, key=int)


def roster_for_season(team_data: Mapping[str, Any], season_id: str) -> list[dict[str, Any]]:
    league = next(
        (row for row in team_data.get("leagues", []) if str(row.get("season_id")) == season_id),
        None,
    )
    if league is None:
        raise ParseError(f"season {season_id}: league metadata missing")
    application = league.get("application_name")
    rosters = (team_data.get("applications") or {}).get("rosters", [])
    roster = next((row for row in rosters if row.get("label") == application), None)
    if roster is None:
        raise ParseError(f"season {season_id}: roster {application!r} missing")
    return roster.get("data") or []


def _player_stats(data: Mapping[str, Any], team_id: str) -> dict[str, int]:
    rows = (data.get("stats") or {}).get("stats") or []
    row = next((item for item in rows if str(item.get("team_id")) == team_id), None) or {}
    additional = {
        str(item.get("name")): int(item.get("value") or 0)
        for item in (
            ((data.get("stats_player") or {}).get("additionalStats") or {}).get("items") or []
        )
    }
    return {
        "played": int(row.get("games") or 0),
        "goals": int(row.get("goals") or 0),
        "assists": int(row.get("assists") or 0),
        "yellow": int(row.get("yellow_cards") or 0),
        "red": int(row.get("red_cards") or 0),
        "mvp": additional.get("MVP", 0),
    }


def _kickoff(row: Mapping[str, Any]) -> datetime | None:
    raw_date = row.get("date")
    if not raw_date:
        return None
    day = date.fromisoformat(str(raw_date))
    raw_time = str(row.get("time") or "00:00:00")
    return datetime.combine(day, time.fromisoformat(raw_time), tzinfo=MSK)


def parse_bundle(
    team_data: Mapping[str, Any],
    matches_data: Mapping[str, Any],
    player_stats: Mapping[str, Mapping[str, Any]],
    season_id: str,
    team_id: str,
    public_base: str,
    api_base: str,
    extra_players: list[dict[str, Any]] | None = None,
) -> JoinFootballBundle:
    matches = [
        row for row in matches_data.get("matches", []) if str(row.get("season_id")) == season_id
    ]
    if not matches:
        raise ParseError(f"season {season_id}: matches missing")

    leagues = [
        row for row in team_data.get("leagues", []) if str(row.get("season_id")) == season_id
    ]
    if not leagues:
        raise ParseError(f"season {season_id}: league metadata missing")
    application = str(leagues[0].get("application_name") or matches[0].get("season_name"))
    days = [date.fromisoformat(str(row["date"])) for row in matches if row.get("date")]
    if not days:
        raise ParseError(f"season {season_id}: match dates missing")

    player_rows = {str(row["id"]): row for row in (extra_players or [])}
    player_rows.update({str(row["id"]): row for row in roster_for_season(team_data, season_id)})
    players = []
    for row in player_rows.values():
        external_id = str(row["id"])
        players.append(
            ParsedPlayer(
                external_id=external_id,
                full_name=f"{row.get('family', '')} {row.get('name', '')}".strip(),
                number=row.get("number"),
                position=POSITION.get(str(row.get("position"))),
                active=False,
                photo_url=_absolute_image(row.get("image"), api_base),
                **_player_stats(player_stats.get(external_id, {}), team_id),
            )
        )

    calendar = []
    for row in matches:
        calendar.append(
            CalendarEntry(
                external_id=str(row["id"]),
                kickoff=_kickoff(row),
                round=row.get("stage_name"),
                venue_name=row.get("stadium_name"),
                venue_address=row.get("stadium_address"),
                home_team_id=str(row["home_team_id"]),
                away_team_id=str(row["guest_team_id"]),
                home_name=str(row["home_team_name"]),
                away_name=str(row["guest_team_name"]),
                home_logo=_absolute_image(row.get("home_team_image"), api_base),
                away_logo=_absolute_image(row.get("guest_team_image"), api_base),
                home_score=row.get("home_team_scores"),
                away_score=row.get("guest_team_scores"),
            )
        )

    return JoinFootballBundle(
        tournament=TournamentInfo(
            external_id=season_id,
            name=f"{application} · InGame",
            period_start=min(days),
            period_end=max(days),
            url=f"{public_base}/amf_5x5/team/{team_id}",
        ),
        players=players,
        calendar=calendar,
        details={},
        standings=[],
        multi_stage=True,
    )
