"""Номера/поля из content/players на ЧИСТОЙ базе (прод: синк контента раньше парсеров)."""

from pathlib import Path

from bu_core.models import Player
from bu_worker.dto import JoinFootballBundle
from bu_worker.pipeline.content import sync_content
from bu_worker.pipeline.joinfootball import ingest
from bu_worker.sources.content import ContentBundle, PlayerContent
from bu_worker.sources.joinfootball.parse import (
    parse_application,
    parse_standings,
    parse_tournament_info,
)
from sqlalchemy import func, select

FIX = Path(__file__).parent / "fixtures" / "joinfootball"


def jf_bundle() -> JoinFootballBundle:
    read = lambda n: (FIX / n).read_text(encoding="utf-8")  # noqa: E731
    info = parse_tournament_info(read("calendar.html"), "1066703", "https://x/tournament/1066703")
    return JoinFootballBundle(
        tournament=info,
        players=parse_application(read("application.html")),
        calendar=[],
        details={},
        standings=parse_standings(read("tables.html")),
    )


def content_with_numbers() -> ContentBundle:
    return ContentBundle(
        club={"name": "Бауман Юнайтед"},
        history={},
        tournaments=[],
        news=[],
        matches={},
        players={
            "aleksandr-korolev": PlayerContent.model_validate({"number": 10}),
            "egor-kucha": PlayerContent.model_validate({"number": 13}),
        },
    )


def test_number_only_override_on_fresh_db_creates_no_placeholder_and_no_duplicate(db):
    sync_content(db, content_with_numbers())  # игроков ещё нет
    assert db.scalar(select(func.count()).select_from(Player)) == 0

    ingest(db, jf_bundle(), "1089660", ["Bauman United"])
    korolev = db.scalars(select(Player).where(Player.last_name == "Королев")).all()
    assert len(korolev) == 1
    assert korolev[0].slug == "aleksandr-korolev"
    assert korolev[0].number == 10  # отложенный номер применился после появления игрока
    assert "number" in korolev[0].manual_fields
    kucha = db.scalars(select(Player).where(Player.slug == "egor-kucha")).one()
    assert kucha.number == 13
    assert db.scalar(select(func.count()).select_from(Player).where(Player.first_name == "")) == 0


def test_cleanup_removes_placeholders_and_restores_slugs(db):
    from bu_core.models import ContentDoc
    from bu_worker.pipeline.cleanup import fix_placeholder_players

    # Состояние прода после старого кода: пустышки из content + настоящие игроки со slug «-2».
    for slug, number in (("aleksandr-korolev", 10), ("egor-kucha", 13)):
        db.add(
            Player(
                slug=slug,
                first_name="",
                last_name=slug,
                number=number,
                aliases=[],
                manual_fields=["number"],
                achievements=[],
            )
        )
    db.add(
        ContentDoc(
            key="player_overrides",
            data={"aleksandr-korolev": {"number": 10}, "egor-kucha": {"number": 13}},
        )
    )
    db.flush()
    ingest(db, jf_bundle(), "1089660", ["Bauman United"])
    # старый код вернул бы номера настоящим только при совпадении slug; имитируем «-2»
    real = db.scalars(select(Player).where(Player.last_name == "Королев")).one()
    real.slug = "aleksandr-korolev-2"
    real.number, real.manual_fields = None, []
    db.flush()

    report = fix_placeholder_players(db)

    assert report.removed == 2
    korolev = db.scalars(select(Player).where(Player.last_name == "Королев")).one()
    assert (korolev.slug, korolev.number) == ("aleksandr-korolev", 10)
    assert db.scalar(select(func.count()).select_from(Player).where(Player.first_name == "")) == 0
    assert db.scalar(select(func.count()).select_from(Player).where(Player.slug.like("%-2"))) == 0
