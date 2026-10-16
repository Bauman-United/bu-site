from datetime import UTC, date, datetime

from bu_core.models import ContentDoc, Match, MatchAppearance, News, Player
from bu_worker.pipeline.content import sync_content
from bu_worker.sources.content import (
    ContentBundle,
    MatchContent,
    NewsContent,
    PlayerContent,
    TournamentContent,
)
from sqlalchemy import select


def make_bundle(**overrides) -> ContentBundle:
    data = dict(
        club={"name": "Бауман Юнайтед"},
        history={"trophies": []},
        tournaments=[],
        players={},
        news=[],
        matches={},
    )
    data.update(overrides)
    return ContentBundle(**data)


def test_club_and_history_docs(db):
    sync_content(db, make_bundle())
    assert db.get(ContentDoc, "club").data["name"] == "Бауман Юнайтед"
    assert db.get(ContentDoc, "history").data == {"trophies": []}


def test_player_fields_and_manual_marks(db):
    existing = Player(
        slug="aleksandr-korolev",
        first_name="Александр",
        last_name="Королев",
        number=10,
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    db.add(existing)
    db.flush()
    yaml_player = PlayerContent.model_validate({"nickname": "Король", "number": 7})
    sync_content(db, make_bundle(players={"aleksandr-korolev": yaml_player}))
    db.refresh(existing)
    assert (existing.nickname, existing.number) == ("Король", 7)
    assert set(existing.manual_fields) == {"nickname", "number"}


def test_new_player_from_yaml(db):
    p = PlayerContent.model_validate(
        {"first_name": "Иван", "last_name": "Петров", "position": "GK"}
    )
    sync_content(db, make_bundle(players={"ivan-petrov": p}))
    created = db.scalars(select(Player).where(Player.slug == "ivan-petrov")).one()
    assert created.position == "GK"


def test_news_full_sync_removes_deleted(db):
    one = NewsContent(slug="a", date=date(2026, 9, 1), tag="club", title="A")
    two = NewsContent(slug="b", date=date(2026, 9, 2), tag="club", title="B")
    sync_content(db, make_bundle(news=[one, two]))
    sync_content(db, make_bundle(news=[two]))
    assert [n.slug for n in db.scalars(select(News))] == ["b"]


def test_manual_match_with_squad_and_events(db):
    korolev = Player(
        slug="aleksandr-korolev",
        first_name="Александр",
        last_name="Королев",
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    db.add(korolev)
    db.flush()
    t = TournamentContent(slug="lfl-2026", name="ЛФЛ 8×8", short="ЛФЛ", season="2026")
    m = MatchContent.model_validate(
        {
            "tournament": "lfl-2026",
            "kickoff": "2026-10-11T14:00:00+03:00",
            "home": True,
            "opponent": {"name": "Энергия"},
            "status": "finished",
            "score": {"us": 3, "them": 1},
            "squad": ["aleksandr-korolev"],
            "mvp": "aleksandr-korolev",
            "events": [
                {"minute": 12, "type": "goal", "team": "us", "player": "aleksandr-korolev"},
                {"minute": 50, "type": "goal", "team": "them", "player": "Сидоров"},
            ],
        }
    )
    sync_content(db, make_bundle(tournaments=[t], matches={"2026-10-11-energiya": m}))
    match = db.scalars(select(Match).where(Match.slug == "2026-10-11-energiya")).one()
    assert (match.source, match.score_us, match.mvp_player_id) == ("manual", 3, korolev.id)
    assert match.events[0].player_id == korolev.id
    assert match.events[1].player_name == "Сидоров" and match.events[1].player_id is None
    assert db.get(MatchAppearance, (match.id, korolev.id)) is not None


def test_deleted_news_slug_is_revalidated(db):
    one = NewsContent(slug="a", date=date(2026, 9, 1), tag="club", title="A")
    sync_content(db, make_bundle(news=[one]))
    result = sync_content(db, make_bundle(news=[]))
    assert "news:a" in result.tags


def test_content_mvp_and_events_mark_manual_fields(db):
    korolev = Player(
        slug="aleksandr-korolev",
        first_name="Александр",
        last_name="Королев",
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    t = TournamentContent(slug="lfl-2026", name="ЛФЛ", short="ЛФЛ", season="2026")
    db.add(korolev)
    db.flush()
    m = MatchContent.model_validate(
        {
            "tournament": "lfl-2026",
            "kickoff": "2026-10-11T14:00:00+03:00",
            "home": True,
            "opponent": {"name": "Энергия"},
            "status": "finished",
            "mvp": "aleksandr-korolev",
            "events": [{"minute": 3, "type": "goal", "team": "us", "player": "aleksandr-korolev"}],
        }
    )
    sync_content(db, make_bundle(tournaments=[t], matches={"x": m}))
    match = db.scalars(select(Match).where(Match.slug == "x")).one()
    assert set(match.manual_fields) == {"mvp", "events"}


def _source_match(db) -> Match:
    t = TournamentContent(slug="cup", name="Кубок", short="Кубок", season="2026")
    sync_content(db, make_bundle(tournaments=[t]))
    from bu_core.models import Tournament

    tournament = db.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
    match = Match(
        slug="kvazar-5877228",
        source="joinfootball",
        external_id="5877228",
        tournament_id=tournament.id,
        season_id=tournament.season_id,
        kickoff=None,
        home=False,
        opponent_name="Квазар",
        status="scheduled",
        venue_name="Металлург",
        manual_fields=[],
    )
    db.add(match)
    db.flush()
    return match


def test_content_sets_kickoff_and_venue_on_source_match(db):
    match = _source_match(db)
    m = MatchContent.model_validate(
        {"kickoff": "2026-10-25T18:30:00", "venue": {"name": "Арена", "address": "Москва"}}
    )
    sync_content(db, make_bundle(matches={"kvazar-5877228": m}))
    db.refresh(match)
    assert match.kickoff == datetime(2026, 10, 25, 15, 30, tzinfo=UTC)
    assert (match.venue_name, match.venue_address) == ("Арена", "Москва")
    assert set(match.manual_fields) == {"kickoff", "venue"}
    assert (match.opponent_name, match.source) == ("Квазар", "joinfootball")


def test_content_without_kickoff_leaves_source_match_alone(db):
    match = _source_match(db)
    sync_content(db, make_bundle(matches={"kvazar-5877228": MatchContent(stream_url="https://s")}))
    db.refresh(match)
    assert match.kickoff is None and match.venue_name == "Металлург"
    assert match.manual_fields == []


def test_legacy_season_maps_to_first_year_with_warning(db):
    from bu_core.models import Tournament

    t = TournamentContent(slug="cup", name="Кубок", short="Кубок", season="2025-26")
    result = sync_content(db, make_bundle(tournaments=[t]))
    tournament = db.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
    assert (tournament.season.slug, tournament.season.label) == ("2025", "2025")
    assert any("2025-26" in w and "2025" in w for w in result.warnings)
