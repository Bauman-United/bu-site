from collections.abc import Callable
from datetime import date

from bu_worker.dto import JoinFootballBundle, MatchDetail
from bu_worker.http import PoliteClient
from bu_worker.sources.joinfootball.parse import (
    ParseError,
    is_multi_stage,
    parse_application,
    parse_calendar,
    parse_match,
    parse_protocol,
    parse_standings,
    parse_team_calendar,
    parse_tournament_info,
)


def fetch_bundle(
    client: PoliteClient,
    tournament_id: str,
    team_id: str,
    base_url: str,
    snapshot: Callable[[str, str], None],
    today: date | None = None,
    team_calendar: str | None = None,
) -> JoinFootballBundle:
    """`today` задан и турнир уже закончился — берём и отзаявленных игроков (история).

    `team_calendar` — путь календаря команды за сезон турнира. В многоэтапном турнире
    (выбор этапа в календаре, как в Urban Cup) календарь турнира показывает один этап —
    недостающие наши матчи берутся из календаря команды, а таблица — только если в ней
    есть наша команда.
    """

    def get(name: str, path: str) -> str:
        html = client.get(path)
        snapshot(name, html)
        return html

    calendar_html = get("calendar", f"/tournament/{tournament_id}/calendar")
    info = parse_tournament_info(
        calendar_html, tournament_id, f"{base_url}/tournament/{tournament_id}"
    )
    multi_stage = team_calendar is not None and is_multi_stage(calendar_html)
    try:
        tournament_calendar = parse_calendar(calendar_html, info.period_start, info.period_end)
    except ParseError:
        if not multi_stage:
            raise
        tournament_calendar = []
    calendar = [e for e in tournament_calendar if team_id in (e.home_team_id, e.away_team_id)]
    if multi_stage and team_calendar is not None:
        known = {e.external_id for e in calendar}
        calendar += [
            e
            for e in parse_team_calendar(
                get("team_calendar", team_calendar),
                tournament_id,
                info.period_start,
                info.period_end,
            )
            if e.external_id not in known
        ]
    players = parse_application(
        get("application", f"/tournament/{tournament_id}/teams/application?team_id={team_id}"),
        departed=today is not None and info.period_end < today,
    )
    tables_html = get("tables", f"/tournament/{tournament_id}/tables")
    try:
        standings = parse_standings(tables_html)
    except ParseError:
        if "кубок" not in info.name.lower() and not multi_stage:
            raise
        standings = []  # у кубка вместо таблицы сетка плей-офф
    if multi_stage and not any(f"/team/{team_id}/" in (r.team_logo or "") for r in standings):
        standings = []  # таблица чужой группы/этапа
    details: dict[str, MatchDetail] = {}
    for entry in calendar:
        if entry.home_score is not None:
            detail = MatchDetail(events=[])
            try:
                detail = parse_match(
                    get(f"match_{entry.external_id}", f"/match/{entry.external_id}")
                )
            except ParseError:
                # Протокол событий может быть пустым даже при заполненном составе.
                pass
            try:
                protocol = parse_protocol(
                    get(
                        f"match_{entry.external_id}_protocol",
                        f"/match/{entry.external_id}?active=protocol",
                    )
                )
                if protocol:
                    detail = detail.model_copy(update={"appearances": protocol})
            except ParseError:
                pass
            if detail.events or detail.appearances or detail.mvp_name:
                details[entry.external_id] = detail
    return JoinFootballBundle(
        tournament=info,
        players=players,
        calendar=calendar,
        details=details,
        standings=standings,
        multi_stage=multi_stage,
    )
