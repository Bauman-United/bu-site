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
    return Settings(
        _env_file=None,
        snapshot_dir=str(tmp_path / "snap"),
        joinfootball_base="https://jf.test",
        joinfootball_tournament_ids=["1066703"],  # фейковый сайт отдаёт только Лигу Инженеров
    )


def test_run_ok_writes_matches_runs_and_aggregates(db, tmp_path):
    status = run_joinfootball(db, settings(tmp_path), fake_site(), Notifier(None, None))
    assert status == "ok"
    assert len(db.scalars(select(Match)).all()) == 9
    run = db.scalars(select(IngestRun)).one()
    assert (run.source, run.status, run.counts["players"]) == ("joinfootball:1066703", "ok", 25)
    assert db.get(Computed, "meta") is not None
    assert list((tmp_path / "snap" / "joinfootball").glob("*/*/calendar.html.gz"))


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


CUP_PAGES = {
    "/tournament/1067299/calendar": "cup_calendar.html",
    "/tournament/1067299/teams/application": "cup_application.html",
    "/tournament/1067299/tables": "cup_tables.html",
}


def test_cup_without_standings_is_ingested(db, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /matches\n")
        pages = {**PAGES, **CUP_PAGES}
        if path in pages:
            return httpx.Response(200, text=(FIX / pages[path]).read_text(encoding="utf-8"))
        if path.startswith("/match/"):
            return httpx.Response(200, text=(FIX / "match_5848533.html").read_text("utf-8"))
        return httpx.Response(404)

    client = PoliteClient(
        "https://jf.test", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )
    s = Settings(
        _env_file=None,
        snapshot_dir=str(tmp_path / "snap"),
        joinfootball_base="https://jf.test",
        joinfootball_tournament_ids=["1066703", "1067299"],
    )
    assert run_joinfootball(db, s, client, Notifier(None, None)) == "ok"
    cup = db.scalars(select(Match).where(Match.external_id == "5877221")).one()
    assert cup.tournament.name == "Кубок Специалистов · Осень 2026"
    assert (cup.score_us, cup.score_them) == (5, 0)


def test_default_settings_include_bauman_league_cup():
    assert "1067299" in Settings(_env_file=None).joinfootball_tournament_ids


def test_match_without_timeline_does_not_fail_tournament(db, tmp_path):
    import re

    no_timeline = re.sub(
        r'<div class="game-timeline__event [^>]*>',
        "<div>",
        (FIX / "match_5848533.html").read_text(encoding="utf-8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(404)
        if path in PAGES:
            return httpx.Response(200, text=(FIX / PAGES[path]).read_text(encoding="utf-8"))
        if path.startswith("/match/"):
            return httpx.Response(200, text=no_timeline)
        return httpx.Response(404)

    client = PoliteClient(
        "https://jf.test", "BaumanUnitedBot/1.0", 0, transport=httpx.MockTransport(handler)
    )
    assert run_joinfootball(db, settings(tmp_path), client, Notifier(None, None)) == "ok"
    m = db.scalars(select(Match).where(Match.external_id == "5848533")).one()
    assert (m.score_us, m.score_them) == (2, 3) and m.events == []
