import functools
import logging
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from bu_core.db import make_engine, make_sessionmaker
from bu_core.models import Match
from bu_core.settings import Settings
from sqlalchemy import select

from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import (
    history_sources,
    make_client,
    make_ingame_client,
    run_history,
    run_ingame,
    run_joinfootball,
    run_lfl,
    run_telegram,
)

log = logging.getLogger(__name__)


def single_flight(fn: Callable[[], None]) -> Callable[[], None]:
    """Не даёт двум запускам задачи идти одновременно: второй просто пропускается."""
    lock = threading.Lock()

    @functools.wraps(fn)
    def wrapper() -> None:
        if not lock.acquire(blocking=False):
            log.info("%s already running, skipped", fn.__name__)
            return
        try:
            fn()
        finally:
            lock.release()

    return wrapper


def start(settings: Settings) -> None:
    sessions = make_sessionmaker(make_engine())
    notifier = Notifier(settings.telegram_bot_token, settings.telegram_chat_id)

    history_day: list[date] = []  # день последнего обхода прошлых сезонов
    telegram_refresh_day: list[date] = []  # раз в день обновляем временные CDN-ссылки фото

    @single_flight
    def scrape() -> None:
        # Один клиент на хост на весь запуск: пауза ≥ request_delay_s и между текущими
        # турнирами, и между прошлыми сезонами того же сайта.
        clients = {name: make_client(settings, name) for name in history_sources(settings)}
        with sessions() as session:
            run_joinfootball(session, settings, clients["joinfootball"], notifier)
            run_lfl(session, settings, clients["lfl"], notifier)
            today = datetime.now(UTC).date()
            if history_day[-1:] != [today]:
                # раз в день: поиск турниров всех сезонов; архивные не перекачиваются
                run_history(session, settings, clients, notifier)
                run_ingame(session, settings, make_ingame_client(settings), notifier)
                history_day[:] = [today]

    @single_flight
    def channel_news() -> None:
        client = PoliteClient(
            settings.tg_base,
            f"BaumanUnitedBot/1.0 (+{settings.site_url})",
            settings.request_delay_s,
        )
        with sessions() as session:
            today = datetime.now(UTC).date()
            full_rescan = telegram_refresh_day[-1:] != [today]
            status = run_telegram(
                session, settings, client, notifier, full_rescan=full_rescan
            )
            if full_rescan and status == "ok":
                telegram_refresh_day[:] = [today]

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
    scheduler.add_job(channel_news, "interval", hours=2, next_run_time=datetime.now(UTC))
    scheduler.add_job(prune, "cron", hour=4)
    scheduler.start()
