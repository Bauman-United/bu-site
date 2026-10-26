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
from sqlalchemy.orm import Session

from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.indexnow import submit_changes
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

LIVE_WINDOW = timedelta(hours=3)
# Протоколы (особенно ЛФЛ) дозаполняют голами и передачами в течение пары дней после матча.
PROTOCOL_WINDOW = timedelta(days=3)
PROTOCOL_EVERY = timedelta(hours=2)


def matchday_due(session: Session, now: datetime, last_scrape: datetime | None) -> bool:
    """Идёт матч — качаем каждые 30 минут; после матча — каждые 2 часа ещё 3 дня."""
    kickoff = session.scalars(
        select(Match.kickoff)
        .where(Match.kickoff <= now, Match.kickoff >= now - PROTOCOL_WINDOW)
        .order_by(Match.kickoff.desc())
        .limit(1)
    ).first()
    if kickoff is None:
        return False
    if kickoff >= now - LIVE_WINDOW:
        return True
    return last_scrape is None or now - last_scrape >= PROTOCOL_EVERY


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
    last_scrape: list[datetime] = []  # начало последнего обхода текущих турниров
    telegram_refresh_day: list[date] = []  # раз в день обновляем временные CDN-ссылки фото

    @single_flight
    def scrape() -> None:
        # Один клиент на хост на весь запуск: пауза ≥ request_delay_s и между текущими
        # турнирами, и между прошлыми сезонами того же сайта.
        last_scrape[:] = [datetime.now(UTC)]
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
            submit_changes(session, settings)

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
            status = run_telegram(session, settings, client, notifier, full_rescan=full_rescan)
            if full_rescan and status == "ok":
                telegram_refresh_day[:] = [today]
            submit_changes(session, settings)

    def matchday() -> None:
        with sessions() as session:
            due = matchday_due(session, datetime.now(UTC), last_scrape[-1] if last_scrape else None)
        if due:
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
    scheduler.add_job(prune, "cron", hour=4, next_run_time=datetime.now(UTC))
    scheduler.start()
