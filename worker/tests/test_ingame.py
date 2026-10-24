import json
from datetime import date

import httpx
from bu_core.models import IngestRun, Match, Player, PlayerSeasonStats, Tournament
from bu_core.settings import Settings
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import run_ingame
from bu_worker.sources.ingame.parse import parse_bundle, roster_for_season, season_ids
from sqlalchemy import select

TEAM = {
    "leagues": [
        {
            "league_id": 187,
            "season_id": 15,
            "season": "2022",
            "league_name": "Второй дивизион",
            "application_name": "Турниры объединённого мира 2022",
        }
    ],
    "applications": {
        "rosters": [
            {
                "label": "Турниры объединённого мира 2022",
                "data": [
                    {
                        "id": 47593,
                        "name": "Алексей",
                        "family": "Калиниченко",
                        "image": "/images/players/47593.png",
                        "position": "Полузащитник",
                        "number": 20,
                    }
                ],
            }
        ]
    },
}
MATCHES = {
    "matches": [
        {
            "id": 54638,
            "home_team_id": 1997,
            "guest_team_id": 169,
            "home_team_scores": 4,
            "guest_team_scores": 2,
            "date": "2022-06-05",
            "time": "21:40:00",
            "season_id": 15,
            "season_name": "2022",
            "stage_name": "1 Тур",
            "stadium_name": "БЕТСИТИ АРЕНА",
            "home_team_name": "Bauman United",
            "guest_team_name": "Витория",
            "home_team_image": "/images/teams/1997.png",
            "guest_team_image": "/images/teams/169.png",
        }
    ]
}
STATS = {
    "stats": {
        "stats": [
            {
                "team_id": 1997,
                "games": 1,
                "goals": 2,
                "assists": 1,
                "yellow_cards": 1,
                "red_cards": 0,
            }
        ]
    },
    "stats_player": {
        "additionalStats": {"items": [{"name": "MVP", "value": 1}]},
        "goalkeeperStats": {
            "items": [
                {"name": "Игры", "value": 12},
                {"name": "ГП", "value": 18},
                {"name": "ГП/Игра", "value": 1.5},
            ]
        },
    },
}
LEADERS = {
    "players": [
        {
            "name": "Голы",
            "players": [
                {
                    "player_id": 47593,
                    "name": "Алексей",
                    "family": "Калиниченко",
                    "image": "/images/players/47593.png",
                    "position": "Полузащитник",
                }
            ],
        }
    ]
}


def test_parse_ingame_season_bundle():
    assert season_ids(MATCHES) == ["15"]
    assert roster_for_season(TEAM, "15")[0]["id"] == 47593
    bundle = parse_bundle(
        TEAM,
        MATCHES,
        {"47593": STATS},
        "15",
        "1997",
        "https://ingame-sports.ru",
        "https://api.ingame-server.ru",
    )
    assert bundle.tournament.period_start == date(2022, 6, 5)
    assert bundle.tournament.name == "Турниры объединённого мира 2022 · InGame"
    assert bundle.players[0].model_dump() == {
        "external_id": "47593",
        "full_name": "Калиниченко Алексей",
        "number": 20,
        "position": "MF",
        "played": 1,
        "goals": 2,
        "assists": 1,
        "yellow": 1,
        "red": 0,
        "mvp": 1,
        "goalkeeper_played": 12,
        "goalkeeper_conceded": 18,
        "active": False,
        "photo_url": "https://api.ingame-server.ru/images/players/47593.png",
    }
    assert bundle.calendar[0].home_score == 4


def test_run_ingame_adds_matches_and_player_stats(db, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/teams/1997/all":
            return httpx.Response(200, json=TEAM)
        if request.url.path == "/teams/1997/matches/v2":
            return httpx.Response(200, json=MATCHES)
        if request.url.path == "/teams/1997/bestPlayers":
            assert json.loads(request.content) == {"event_id": 1, "season_id": 15}
            return httpx.Response(200, json=LEADERS)
        if request.url.path == "/players/47593/statistics":
            assert json.loads(request.content) == {"season_id": 15, "team_id": 1997}
            return httpx.Response(200, json=STATS)
        return httpx.Response(404)

    client = PoliteClient(
        "https://api.test",
        "BaumanUnitedBot/1.0",
        0,
        transport=httpx.MockTransport(handler),
    )
    settings = Settings(
        _env_file=None,
        ingame_base="https://api.test",
        snapshot_dir=str(tmp_path / "snapshots"),
        request_delay_s=0,
    )
    status = run_ingame(db, settings, client, Notifier(None, None), today=date(2026, 10, 17))
    assert status == "ok"
    match = db.scalars(select(Match)).one()
    assert (match.source, match.score_us, match.score_them) == ("ingame", 4, 2)
    assert match.source_url == "https://ingame-sports.ru/amf_5x5/match/54638"
    player = db.scalars(select(Player)).one()
    stats = db.scalars(select(PlayerSeasonStats)).one()
    assert (player.first_name, player.last_name, player.active) == (
        "Алексей",
        "Калиниченко",
        False,
    )
    assert (stats.played, stats.goals, stats.assists, stats.mvp) == (1, 2, 1, 1)
    tournament = db.scalars(select(Tournament)).one()
    assert (tournament.source, tournament.season.slug) == ("ingame", "2022")
    run = db.scalars(select(IngestRun)).one()
    assert (run.source, run.status) == ("ingame:15", "ok")
    assert list((tmp_path / "snapshots" / "ingame").glob("*/*.json.gz"))

    # Архивный сезон при обычном ежедневном запуске не перекачивается.
    assert run_ingame(db, settings, client, Notifier(None, None), today=date(2026, 10, 18)) == "ok"
    assert len(db.scalars(select(IngestRun)).all()) == 1
