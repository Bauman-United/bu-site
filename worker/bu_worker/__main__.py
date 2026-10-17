import argparse
import logging
import sys

from bu_core.db import make_engine, make_sessionmaker
from bu_core.settings import get_settings

from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import (
    history_sources,
    make_client,
    make_ingame_client,
    run_content,
    run_history,
    run_ingame,
    run_joinfootball,
    run_lfl,
    run_migrate_seasons,
    run_telegram,
)


def main() -> int:
    settings = get_settings()
    # лиги joinsport без текущих турниров (IFL, Urban Cup): `run <key>` — их прошлые турниры
    leagues = [j.key for j in settings.joinsport_leagues]
    parser = argparse.ArgumentParser(prog="bu_worker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument(
        "source",
        choices=[
            "joinfootball",
            "lfl",
            "ingame",
            *leagues,
            "history",
            "telegram",
            "content",
            "all",
        ],
        help="history — все прошлые сезоны всех лиг; ifl, urban — прошлые турниры лиги",
    )
    run.add_argument(
        "--limit-tournaments",
        type=int,
        default=None,
        help="history/ifl/urban: не больше N турниров на источник (проверка на живом сайте)",
    )
    run.add_argument(
        "--refresh",
        action="store_true",
        default=None,
        help="перекачать и архивные турниры (то же, что BU_HISTORY_REFRESH=1)",
    )
    sub.add_parser("schedule")
    sub.add_parser(
        "migrate-seasons",
        help="разово: сезоны «2026-27» → календарные годы «2026» (идемпотентно)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # URL Telegram содержит токен

    if args.cmd == "schedule":
        from bu_worker.schedule import start

        start(settings)
        return 0

    sessions = make_sessionmaker(make_engine())
    if args.cmd == "migrate-seasons":
        return run_migrate_seasons(sessions, settings)

    notifier = Notifier(settings.telegram_bot_token, settings.telegram_chat_id)
    status = "ok"
    with sessions() as session:
        if args.source in ("content", "all"):
            status = run_content(session, settings)
        if args.source in ("joinfootball", "all"):
            client = make_client(settings, "joinfootball")
            status = run_joinfootball(session, settings, client, notifier, refresh=args.refresh)
        if args.source in ("lfl", "all"):
            client = make_client(settings, "lfl")
            lfl_status = run_lfl(session, settings, client, notifier, refresh=args.refresh)
            if lfl_status != "ok":
                status = lfl_status
        if args.source in ("ingame", "all"):
            ingame_status = run_ingame(
                session,
                settings,
                make_ingame_client(settings),
                notifier,
                refresh=args.refresh,
            )
            if ingame_status != "ok":
                status = ingame_status
        if args.source == "history" or args.source in leagues:
            sources = history_sources(settings) if args.source == "history" else (args.source,)
            status = run_history(
                session,
                settings,
                {name: make_client(settings, name) for name in sources},
                notifier,
                sources=sources,
                limit=args.limit_tournaments,
                refresh=args.refresh,
            )
        if args.source in ("telegram", "all"):
            client = PoliteClient(
                settings.tg_base,
                f"BaumanUnitedBot/1.0 (+{settings.site_url})",
                settings.request_delay_s,
            )
            tg_status = run_telegram(session, settings, client, notifier)
            if tg_status != "ok":
                status = tg_status
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
