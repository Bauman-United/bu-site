import threading
from datetime import UTC, date, datetime, timedelta

from bu_core.models import Match, Tournament
from bu_worker.pipeline.common import ensure_season
from bu_worker.schedule import matchday_due, single_flight


def test_single_flight_skips_overlapping_runs():
    started, release = threading.Event(), threading.Event()
    calls = []

    @single_flight
    def job():
        calls.append(1)
        started.set()
        release.wait(2)

    t = threading.Thread(target=job)
    t.start()
    started.wait(2)
    job()  # пока первый запуск идёт — пропускается
    release.set()
    t.join()
    assert len(calls) == 1


NOW = datetime(2026, 10, 26, 15, 0, tzinfo=UTC)


def _match(db, kickoff: datetime) -> None:
    season = ensure_season(db, "2026")
    tournament = Tournament(
        source="lfl",
        external_id="1",
        slug="t",
        name="T",
        short="T",
        period_end=date(2026, 12, 31),
        season_id=season.id,
    )
    db.add(tournament)
    db.flush()
    db.add(
        Match(
            slug="m",
            tournament_id=tournament.id,
            season_id=season.id,
            kickoff=kickoff,
            home=True,
            opponent_name="Соперник",
            status="finished",
            source="lfl",
        )
    )
    db.flush()


def test_matchday_scrapes_live_match_every_time(db):
    _match(db, NOW - timedelta(hours=1))
    assert matchday_due(db, NOW, last_scrape=NOW - timedelta(minutes=30))


def test_matchday_keeps_refreshing_protocol_for_three_days(db):
    # протокол ЛФЛ (голы, передачи) дозаполняют в течение пары дней после матча
    _match(db, NOW - timedelta(days=2))
    assert matchday_due(db, NOW, last_scrape=None)
    assert matchday_due(db, NOW, last_scrape=NOW - timedelta(hours=2))
    assert not matchday_due(db, NOW, last_scrape=NOW - timedelta(minutes=90))


def test_matchday_idle_without_recent_matches(db):
    _match(db, NOW - timedelta(days=4))
    assert not matchday_due(db, NOW, last_scrape=None)
