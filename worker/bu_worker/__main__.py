import argparse
import logging
import sys

from bu_core.db import make_engine, make_sessionmaker
from bu_core.settings import get_settings

from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import run_content, run_joinfootball


def main() -> int:
    parser = argparse.ArgumentParser(prog="bu_worker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("source", choices=["joinfootball", "content", "all"])
    sub.add_parser("schedule")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # URL Telegram содержит токен

    settings = get_settings()
    if args.cmd == "schedule":
        from bu_worker.schedule import start

        start(settings)
        return 0

    sessions = make_sessionmaker(make_engine())
    notifier = Notifier(settings.telegram_bot_token, settings.telegram_chat_id)
    status = "ok"
    with sessions() as session:
        if args.source in ("content", "all"):
            status = run_content(session, settings)
        if args.source in ("joinfootball", "all"):
            client = PoliteClient(
                settings.joinfootball_base,
                f"BaumanUnitedBot/1.0 (+{settings.site_url})",
                settings.request_delay_s,
            )
            status = run_joinfootball(session, settings, client, notifier)
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
