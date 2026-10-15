from pathlib import Path

import httpx
from bu_core.models import Computed, IngestRun, Match
from bu_core.settings import Settings
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import revalidate, run_joinfootball
from sqlalchemy import select

FIX = Path(__file__).parent / "fixtures" / "joinfootball"
PAGES = {
    "/tournament/1066703/calendar": "calendar.html",
    "/tournament/1066703/teams/application": "application.html",
    "/tournament/1066703/tables": "tables.html",
}


def fake_site(broken: bool = False):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /matches\n")
        if path in PAGES:
            name = PAGES[path]
            if broken and name == "application.html":
                return httpx.Response(200, text="<html>maintenance</html>")
            return httpx.Response(200, text=(FIX / name).read_text(encoding="utf-8"))
        if path.startswith("/match/"):
            return httpx.Response(200, text=(FIX / "match_5848533.html").read_text("utf-8"))
        return httpx.Response(404)

    return PoliteClient(
        "https://jf.test", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )


def settings(tmp_path) -> Settings:
    return Settings(snapshot_dir=str(tmp_path / "snap"), joinfootball_base="https://jf.test")


def test_run_ok_writes_matches_runs_and_aggregates(db, tmp_path):
    status = run_joinfootball(db, settings(tmp_path), fake_site(), Notifier(None, None))
    assert status == "ok"
    assert len(db.scalars(select(Match)).all()) == 9
    run = db.scalars(select(IngestRun)).one()
    assert (run.source, run.status, run.counts["players"]) == ("joinfootball:1066703", "ok", 25)
    assert db.get(Computed, "meta") is not None
    assert list((tmp_path / "snap" / "joinfootball").glob("*/*/calendar.html"))


def test_run_with_broken_page_keeps_old_data(db, tmp_path):
    run_joinfootball(db, settings(tmp_path), fake_site(), Notifier(None, None))
    status = run_joinfootball(db, settings(tmp_path), fake_site(broken=True), Notifier(None, None))
    assert status == "error"
    assert len(db.scalars(select(Match)).all()) == 9
    statuses = [r.status for r in db.scalars(select(IngestRun).order_by(IngestRun.id))]
    assert statuses == ["ok", "error"]


def test_revalidate_posts_tags():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = request.content
        return httpx.Response(200)

    s = Settings(revalidate_url="https://web.test/api/revalidate", revalidate_secret="s3")
    revalidate(s, {"matches", "home"}, transport=httpx.MockTransport(handler))
    assert seen["auth"] == "Bearer s3"
    assert b'"home"' in seen["body"] and b'"matches"' in seen["body"]
