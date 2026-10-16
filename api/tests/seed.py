from datetime import UTC, date, datetime

from bu_core.models import (
    ContentDoc,
    Match,
    MatchEvent,
    News,
    Player,
    PlayerTournamentStats,
    Season,
    StandingRow,
    Tournament,
)
from bu_core.recompute import recompute
from sqlalchemy.orm import Session


def seed(db: Session) -> dict:
    season = Season(slug="2026", label="2026")
    t = Tournament(
        slug="liga-inzhenerov",
        name="Лига Инженеров · Осень 2026",
        short="Лига Инженеров",
        source="joinfootball",
        external_id="1066703",
        season=season,
        url="https://jf/tournament/1066703",
    )
    korolev = Player(
        slug="aleksandr-korolev",
        first_name="Александр",
        last_name="Королев",
        number=10,
        position="MF",
        aliases=[],
        manual_fields=[],
        achievements=[],
        nickname="Король",
    )
    gk = Player(
        slug="egor-kucha",
        first_name="Егор",
        last_name="Куча",
        number=1,
        position="GK",
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    old = Player(
        slug="old-boy",
        first_name="Старый",
        last_name="Игрок",
        position="FW",
        active=False,
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    db.add_all([season, t, korolev, gk, old])
    db.flush()
    db.add_all(
        [
            PlayerTournamentStats(
                player_id=korolev.id, tournament_id=t.id, played=5, goals=2, assists=6
            ),
            PlayerTournamentStats(player_id=gk.id, tournament_id=t.id, played=2),
        ]
    )
    m1 = Match(
        slug="2026-09-06-bauman-junior",
        tournament_id=t.id,
        season_id=season.id,
        round="1 тур",
        kickoff=datetime(2026, 9, 6, 17, 30, tzinfo=UTC),
        home=True,
        venue_name="Металлург",
        opponent_name="Bauman Junior",
        status="finished",
        score_us=2,
        score_them=3,
        source="joinfootball",
        external_id="5848533",
        report_news_slug="start",
    )
    m1.events.extend(
        [
            MatchEvent(minute=19, type="goal", team="them", player_name="Горевой Александр"),
            MatchEvent(
                minute=22,
                type="goal",
                team="us",
                player_id=korolev.id,
                player_name="Королев Александр",
            ),
        ]
    )
    m2 = Match(
        slug="2026-10-25-messiya",
        tournament_id=t.id,
        season_id=season.id,
        round="6 тур",
        kickoff=datetime(2030, 10, 25, 18, 30, tzinfo=UTC),
        home=False,
        opponent_name="Мессия",
        status="scheduled",
        source="joinfootball",
        external_id="5922873",
    )
    db.add_all([m1, m2])
    db.add_all(
        [
            StandingRow(
                tournament_id=t.id,
                pos=1,
                team_name="Раскат",
                played=5,
                won=5,
                drawn=0,
                lost=0,
                gf=21,
                ga=4,
                pts=15,
                updated_at=datetime(2026, 10, 12, tzinfo=UTC),
            ),
            StandingRow(
                tournament_id=t.id,
                pos=6,
                team_name="Bauman United",
                played=5,
                won=2,
                drawn=0,
                lost=3,
                gf=17,
                ga=19,
                pts=6,
                is_us=True,
                updated_at=datetime(2026, 10, 12, tzinfo=UTC),
            ),
        ]
    )
    db.add_all(
        [
            News(
                slug="start",
                date=date(2026, 9, 6),
                tag="match",
                title="Старт",
                body_md="Текст",
                match_slug="2026-09-06-bauman-junior",
            ),
            News(slug="club-news", date=date(2026, 9, 10), tag="club", title="Клуб", body_md=""),
        ]
    )
    db.add(
        ContentDoc(
            key="club", data={"name": "Бауман Юнайтед", "founded": 2019, "primary_tournament": None}
        )
    )
    db.flush()
    recompute(db)
    return {"season": season, "tournament": t, "korolev": korolev}


def seed_lfl(db: Session, ctx: dict) -> Tournament:
    """Второй турнир сезона — ЛФЛ: сыгранный матч и таблица из 7 команд (мы — 5-е)."""
    lfl = Tournament(
        slug="lfl-8x8-2026",
        name="ЛФЛ 8×8 · 2026",
        short="ЛФЛ",
        source="lfl",
        external_id="lfl-1",
        season=ctx["season"],
        url="https://lfl.ru/tournament1",
    )
    db.add(lfl)
    db.flush()
    db.add(
        Match(
            slug="2026-08-30-politekh",
            tournament_id=lfl.id,
            season_id=ctx["season"].id,
            round="1 тур",
            kickoff=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
            home=True,
            opponent_name="Политех",
            status="finished",
            score_us=4,
            score_them=4,
            source="lfl",
            external_id="lfl-m1",
        )
    )
    for pos in range(1, 8):
        db.add(
            StandingRow(
                tournament_id=lfl.id,
                pos=pos,
                team_name="Bauman United" if pos == 5 else f"Команда {pos}",
                played=1,
                won=0,
                drawn=1,
                lost=0,
                gf=4,
                ga=4,
                pts=8 - pos,
                is_us=pos == 5,
                updated_at=datetime(2026, 9, 1, tzinfo=UTC),
            )
        )
    db.flush()
    recompute(db)
    return lfl
