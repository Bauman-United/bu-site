import json
from datetime import UTC, date, datetime

import httpx
from bu_core.models import Computed, Match, News, Season, Tournament
from bu_core.settings import Settings
from bu_worker.indexnow import STATE_KEY, changed_paths, submit_changes

SITE = "https://baumanunited.ru"


def settings(**kw) -> Settings:
    return Settings(site_url=SITE, indexnow_key="k3y", **kw)


def capture(status: int = 200):
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(status)

    return calls, httpx.MockTransport(handler)


def add_match(db, slug: str, updated: datetime) -> Match:
    season = db.query(Season).first() or Season(slug="2026", label="2026")
    db.add(season)
    db.flush()
    t = db.query(Tournament).first() or Tournament(
        slug="t", name="Лига", short="Л", season_id=season.id, source="test"
    )
    db.add(t)
    db.flush()
    m = Match(
        slug=slug,
        tournament_id=t.id,
        season_id=season.id,
        home=True,
        opponent_name="X",
        status="finished",
        source="test",
    )
    db.add(m)
    db.flush()
    m.updated_at = updated
    db.flush()
    return m


def test_changed_paths_new_changed_removed():
    sent = {"/": "2026-10-01", "/matches/a": "2026-10-01", "/news/gone": "2026-09-01"}
    entries = [("/", date(2026, 10, 1)), ("/matches/a", date(2026, 10, 2)), ("/team/b", None)]
    paths, current = changed_paths(entries, sent)
    assert paths == ["/matches/a", "/team/b", "/news/gone"]
    assert current == {"/": "2026-10-01", "/matches/a": "2026-10-02", "/team/b": ""}


def test_no_key_no_request(db):
    calls, transport = capture()
    assert submit_changes(db, Settings(site_url=SITE), transport=transport) == 0
    assert calls == []


def test_submits_only_changes_between_runs(db):
    add_match(db, "m1", datetime(2026, 10, 1, tzinfo=UTC))
    db.add(News(slug="n1", date=date(2026, 10, 1), tag="club", title="t", body_md=""))
    db.flush()

    calls, transport = capture(202)
    sent = submit_changes(db, settings(), transport=transport)
    assert sent > 0
    body = calls[0]
    assert body["host"] == "baumanunited.ru"
    assert body["key"] == "k3y"
    assert body["keyLocation"] == f"{SITE}/indexnow.txt"
    assert {f"{SITE}/matches/m1", f"{SITE}/news/n1", f"{SITE}/"} <= set(body["urlList"])

    # ничего не менялось — запроса нет
    calls.clear()
    assert submit_changes(db, settings(), transport=transport) == 0
    assert calls == []

    # матч обновился — уходят он и разделы, которые от него зависят
    m = db.query(Match).filter_by(slug="m1").one()
    m.updated_at = datetime(2026, 10, 5, tzinfo=UTC)
    db.flush()
    submit_changes(db, settings(), transport=transport)
    urls = set(calls[0]["urlList"])
    assert f"{SITE}/matches/m1" in urls and f"{SITE}/matches" in urls
    assert f"{SITE}/news/n1" not in urls


def test_failure_keeps_state_for_retry(db):
    add_match(db, "m2", datetime(2026, 10, 1, tzinfo=UTC))
    calls, transport = capture(429)
    assert submit_changes(db, settings(), transport=transport) == 0
    assert db.get(Computed, STATE_KEY) is None
    ok_calls, ok = capture(200)
    assert submit_changes(db, settings(), transport=ok) > 0
