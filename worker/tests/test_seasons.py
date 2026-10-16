from datetime import UTC, date, datetime

import pytest
from bu_core.models import Computed, Match, Season, Tournament
from bu_worker.pipeline.common import ensure_season, season_slug, season_slug_for
from bu_worker.pipeline.seasons import migrate_seasons
from sqlalchemy import select


@pytest.mark.parametrize(
    ("d", "slug"),
    [(date(2026, 3, 1), "2026"), (date(2026, 9, 1), "2026"), (date(2019, 12, 31), "2019")],
)
def test_season_is_calendar_year(d, slug):
    assert season_slug_for(d) == slug


def test_ensure_season_label_is_year(db):
    season = ensure_season(db, "2026")
    assert (season.slug, season.label) == ("2026", "2026")
    assert ensure_season(db, "2026").id == season.id


@pytest.mark.parametrize(
    ("value", "slug", "legacy"),
    [("2026", "2026", False), (2026, "2026", False), ("2026-27", "2026", True)],
)
def test_season_slug_accepts_legacy(value, slug, legacy):
    assert season_slug(value) == (slug, legacy)


def test_season_slug_rejects_garbage():
    with pytest.raises(ValueError):
        season_slug("осень")


def _tournament(db, slug: str, name: str, season: Season, source: str = "joinfootball"):
    t = Tournament(slug=slug, name=name, short=slug, source=source, external_id=slug, season=season)
    db.add(t)
    db.flush()
    return t


def _match(db, slug: str, t: Tournament, kickoff: datetime | None) -> Match:
    m = Match(
        slug=slug,
        tournament_id=t.id,
        season_id=t.season_id,
        home=True,
        kickoff=kickoff,
        opponent_name="X",
        status="finished",
        score_us=1,
        score_them=0,
        source=t.source,
        external_id=slug,
    )
    db.add(m)
    db.flush()
    return m


def test_migrate_seasons_moves_everything_to_calendar_years(db):
    s1920 = Season(slug="2019-20", label="2019/20", final_place="1 место")
    s2526 = Season(slug="2025-26", label="2025/26")
    s2627 = Season(slug="2026-27", label="2026/27")
    db.add_all([s1920, s2526, s2627])
    db.flush()
    spring = _tournament(db, "bl-spring-26", "Весна 2026", s2526)
    autumn = _tournament(db, "bl-autumn-26", "Осень 2026", s2627)
    lfl = _tournament(db, "lfl-26", "2-й дивизион А ВЛ-2026", s2627, source="lfl")
    old = _tournament(db, "cup-19", "Кубок", s1920, source="manual")
    m_spring = _match(db, "m-spring", spring, datetime(2026, 3, 14, tzinfo=UTC))
    _match(db, "m-spring-undated", spring, None)
    m_autumn = _match(db, "m-autumn", autumn, datetime(2026, 9, 6, tzinfo=UTC))
    m_old = _match(db, "m-old", old, None)
    db.add(Computed(key="season:2025-26", data={}))
    db.flush()

    report = migrate_seasons(db)

    seasons = {s.slug: s for s in db.scalars(select(Season))}
    assert set(seasons) == {"2019", "2026"}
    assert seasons["2026"].label == "2026"
    assert seasons["2019"].final_place == "1 место"
    for t in (spring, autumn, lfl):
        db.refresh(t)
        assert t.season.slug == "2026"
    db.refresh(old)
    assert old.season.slug == "2019"
    for m in (m_spring, m_autumn):
        db.refresh(m)
        assert m.season_id == seasons["2026"].id
    db.refresh(m_old)
    assert m_old.season_id == seasons["2019"].id
    undated = db.scalars(select(Match).where(Match.slug == "m-spring-undated")).one()
    assert undated.season_id == seasons["2026"].id
    assert report["tournaments_moved"] == 4
    assert report["seasons_deleted"] == 3

    assert db.get(Computed, "meta").data == {"current_season": "2026"}
    assert db.get(Computed, "season:2026") is not None
    assert db.get(Computed, "season:2025-26") is None


def test_migrate_seasons_is_idempotent(db):
    s = Season(slug="2026", label="2026")
    db.add(s)
    db.flush()
    t = _tournament(db, "bl", "Осень 2026", s)
    _match(db, "m", t, datetime(2026, 9, 6, tzinfo=UTC))
    assert migrate_seasons(db)["tournaments_moved"] == 0
    assert migrate_seasons(db) == {"tournaments_moved": 0, "matches_moved": 0, "seasons_deleted": 0}
    assert [x.slug for x in db.scalars(select(Season))] == ["2026"]
