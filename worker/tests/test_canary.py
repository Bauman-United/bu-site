"""Живая проверка, что вёрстка join.football всё ещё парсится.

Запуск: CANARY=1 uv run pytest -m canary
"""

import os

import pytest
from bu_core.settings import Settings
from bu_worker.http import PoliteClient
from bu_worker.sources.joinfootball.fetch import fetch_bundle

pytestmark = [
    pytest.mark.canary,
    pytest.mark.skipif(os.environ.get("CANARY") != "1", reason="live network check"),
]


def test_live_joinfootball_still_parses():
    s = Settings(_env_file=None)
    client = PoliteClient(s.joinfootball_base, "BaumanUnitedBot/1.0 (+canary)", s.request_delay_s)
    bundle = fetch_bundle(
        client,
        s.joinfootball_tournament_ids[0],
        s.joinfootball_team_id,
        s.joinfootball_base,
        lambda name, html: None,
    )
    assert len(bundle.players) >= 8
    assert bundle.calendar
    assert any(row.team_name in s.our_team_names for row in bundle.standings)
