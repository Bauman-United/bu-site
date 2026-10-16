"""Фото игрока: ручное из content/ > join.football (БЛ) > ЛФЛ."""

from datetime import date

from bu_core.models import Player
from bu_worker.dto import JoinFootballBundle, ParsedPlayer, TournamentInfo
from bu_worker.pipeline.joinfootball import ingest as ingest_jf
from bu_worker.pipeline.lfl import ingest as ingest_lfl
from sqlalchemy import select

JF_PHOTO = "https://st.joinsport.io/player/2079261/photo/68beabf36ef3a.jpg"
LFL_KOROLEV = "https://lfl.ru/photo/persons/source/217632.jpg"
LFL_DOLZHENKOV = "https://lfl.ru/photo/persons/source/192766.jpg"


def player(ext: str, name: str, photo: str | None) -> ParsedPlayer:
    return ParsedPlayer(
        external_id=ext,
        full_name=name,
        number=None,
        position="MF",
        played=1,
        goals=0,
        assists=0,
        yellow=0,
        red=0,
        photo_url=photo,
    )


def bundle(source_id: str, url: str, players: list[ParsedPlayer]) -> JoinFootballBundle:
    info = TournamentInfo(
        external_id=source_id,
        name=f"Турнир {source_id}",
        period_start=date(2026, 9, 1),
        period_end=date(2026, 12, 1),
        url=url,
    )
    return JoinFootballBundle(
        tournament=info, players=players, calendar=[], details={}, standings=[]
    )


def jf(players: list[ParsedPlayer]) -> JoinFootballBundle:
    return bundle("1066703", "https://jf.test/tournament/1066703", players)


def lfl(players: list[ParsedPlayer]) -> JoinFootballBundle:
    return bundle("32573", "https://lfl.ru/tournament32573", players)


def run_lfl(db, players: list[ParsedPlayer]) -> None:
    ingest_lfl(
        db, lfl(players), "14270", ["Бауман Юнайтед"], lambda mid: f"https://lfl.ru/match{mid}"
    )


def get(db, slug: str) -> Player:
    return db.scalars(select(Player).where(Player.slug == slug)).one()


def test_lfl_photo_does_not_replace_joinfootball_photo(db):
    ingest_jf(db, jf([player("2079261", "Королев Александр", JF_PHOTO)]), "1089660", [])
    run_lfl(
        db,
        [
            player("266203", "Королёв Александр", LFL_KOROLEV),
            player("282208", "Долженков Артём", LFL_DOLZHENKOV),
        ],
    )
    assert get(db, "aleksandr-korolev").photo == JF_PHOTO
    assert get(db, "artem-dolzhenkov").photo == LFL_DOLZHENKOV


def test_joinfootball_photo_replaces_lfl_photo(db):
    run_lfl(db, [player("266203", "Королёв Александр", LFL_KOROLEV)])
    assert get(db, "aleksandr-korolev").photo == LFL_KOROLEV
    ingest_jf(db, jf([player("2079261", "Королев Александр", JF_PHOTO)]), "1089660", [])
    assert get(db, "aleksandr-korolev").photo == JF_PHOTO


def test_lfl_fills_photo_when_joinfootball_has_none(db):
    ingest_jf(db, jf([player("2079261", "Королев Александр", None)]), "1089660", [])
    run_lfl(db, [player("266203", "Королёв Александр", LFL_KOROLEV)])
    assert get(db, "aleksandr-korolev").photo == LFL_KOROLEV
