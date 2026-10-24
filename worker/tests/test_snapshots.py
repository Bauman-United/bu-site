import gzip
from datetime import UTC, datetime, timedelta

from bu_worker.snapshots import prune, save

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def test_prune_keeps_recent_and_removes_old(tmp_path):
    fresh = save(tmp_path, "joinfootball/1066703", "calendar", "<html/>", NOW)
    old = save(tmp_path, "joinfootball/1066703", "calendar", "<html/>", NOW - timedelta(days=40))
    assert prune(tmp_path, 30, NOW) == 1
    assert fresh.exists()
    assert not old.exists()


def test_save_writes_gzip(tmp_path):
    path = save(tmp_path, "lfl/1", "calendar", "<html>Бауман</html>", NOW)
    assert path.name == "calendar.html.gz"
    assert gzip.decompress(path.read_bytes()).decode("utf-8") == "<html>Бауман</html>"
