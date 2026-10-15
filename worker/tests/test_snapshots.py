from datetime import UTC, datetime, timedelta

from bu_worker.snapshots import prune, save

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def test_prune_keeps_recent_and_removes_old(tmp_path):
    fresh = save(tmp_path, "joinfootball/1066703", "calendar", "<html/>", NOW)
    old = save(tmp_path, "joinfootball/1066703", "calendar", "<html/>", NOW - timedelta(days=40))
    assert prune(tmp_path, 30, NOW) == 1
    assert fresh.exists()
    assert not old.exists()
