import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from bu_core.db import make_engine, make_sessionmaker
from bu_core.models import Match
from bu_core.settings import Settings
from sqlalchemy import select

from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import run_joinfootball

log = logging.getLogger(__name__)


def start(settings: Settings) -> None:
    sessions = make_sessionmaker(make_engine())
    notifier = Notifier(settings.telegram_bot_token, settings.telegram_chat_id)

    def scrape() -> None:
        client = PoliteClient(
            settings.joinfootball_base,
            f"BaumanUnitedBot/1.0 (+{settings.site_url})",
            settings.request_delay_s,
        )
        with sessions() as session:
            run_joinfootball(session, settings, client, notifier)

    def matchday() -> None:
        now = datetime.now(UTC)
        with sessions() as session:
            live = session.scalars(
                select(Match.id).where(
                    Match.kickoff <= now, Match.kickoff >= now - timedelta(hours=3)
                )
            ).first()
        if live is not None:
            scrape()

    def prune() -> None:
        removed = snapshots.prune(
            Path(settings.snapshot_dir), settings.snapshot_keep_days, datetime.now(UTC)
        )
        log.info("pruned %s snapshot folders", removed)

    scheduler = BlockingScheduler(timezone="Europe/Moscow")
    scheduler.add_job(scrape, "interval", hours=6, next_run_time=datetime.now(UTC))
    scheduler.add_job(matchday, "interval", minutes=30)
    scheduler.add_job(prune, "cron", hour=4)
    scheduler.start()
