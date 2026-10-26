from datetime import UTC, date, datetime

from bu_core.models import IngestRun, Tournament
from bu_worker.pipeline.common import ensure_season
from bu_worker.pipeline.joinfootball import is_archived


def _tournament(db, source: str) -> None:
    season = ensure_season(db, "2025")
    db.add(
        Tournament(
            source=source,
            external_id="1",
            slug=f"{source}-2025",
            name="Турнир 2025",
            short="Турнир",
            kind="league",
            period_end=date(2025, 12, 31),
            season_id=season.id,
        )
    )


def _run(db, source: str, counts: dict, day: int = 20) -> None:
    db.add(
        IngestRun(
            source=f"{source}:1",
            started_at=datetime(2026, 1, day, tzinfo=UTC),
            finished_at=datetime(2026, 1, day, tzinfo=UTC),
            status="ok",
            counts=counts,
        )
    )
    db.flush()


def test_lfl_archive_imported_before_assists_is_refetched_once(db):
    _tournament(db, "lfl")
    _run(db, "lfl", {"players": 20, "matches": 28, "protocols": 26})
    assert not is_archived(db, "lfl", "1", date(2026, 10, 26))
    _run(db, "lfl", {"players": 20, "matches": 28, "protocols": 26, "assists": 90}, day=21)
    assert is_archived(db, "lfl", "1", date(2026, 10, 26))


def test_other_sources_do_not_need_assists_marker(db):
    _tournament(db, "joinfootball")
    _run(db, "joinfootball", {"players": 20, "matches": 10, "protocols": 10})
    assert is_archived(db, "joinfootball", "1", date(2026, 10, 26))
