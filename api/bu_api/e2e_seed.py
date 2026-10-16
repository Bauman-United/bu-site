"""Детерминированные данные для Playwright: python -m bu_api.e2e_seed <url> [--empty]."""

import sys
from datetime import UTC, date, datetime
from typing import Any

from bu_core.models import (
    Base,
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
from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import Session

CLUB = {
    "name": "Бауман Юнайтед",
    "name_en": "Bauman United",
    "founded": 2019,
    "city": "Москва",
    "university": "МГТУ им. Н. Э. Баумана",
    "format": "8x8",
    "primary_tournament": None,
    "socials": {
        "telegram": "https://t.me/baumanunited",
        "vk": "https://vk.com/baumanunited",
        "youtube": None,
        "lfl": "https://lfl.ru/club14270",
        "joinfootball": None,
    },
    "contacts": {
        "captain_name": "Александр Королев",
        "captain_telegram": "https://t.me/captain",
        "email": "team@example.com",
    },
    "training": {
        "days": "Вторник и четверг",
        "time": "20:00",
        "place": "Спорткомплекс МГТУ",
        "map_url": "https://yandex.ru/maps/-/test",
    },
    "looking_for": ["Вратаря", "Защитника ×2"],
    "player_of_month": {"player": "aleksandr-korolev", "month": "2026-10", "stat": "3 гола"},
}


def _player(slug, first, last, number, position, **extra):
    return Player(
        slug=slug,
        first_name=first,
        last_name=last,
        number=number,
        position=position,
        aliases=[],
        manual_fields=[],
        achievements=[],
        **extra,
    )


# В пустой БД — только «трофей» без названия: цифры клуба на главной его считают, /history прячет.
EMPTY_HISTORY: dict[str, Any] = {"timeline": [], "trophies": [{"place": 1}], "legends": []}
HISTORY: dict[str, Any] = {
    "timeline": [
        {"year": "2019", "tag": "Основание", "title": "Основание команды", "highlight": True},
        {"year": "Весна 2021", "tag": "BL", "title": "Серебро первого дивизиона BL"},
        {
            "year": "Осень 2023",
            "tag": "BL",
            "title": "Победа в Кубке BL",
            "text": "Финал на стадионе МГТУ.",
            "highlight": True,
        },
    ],
    "trophies": [
        {"place": 2, "title": "Bauman League, первый дивизион", "season": "Весна 2021"},
        {"place": 1, "title": "Кубок BL", "season": "Осень 2023"},
        {"place": 3, "title": "IFL, второй дивизион", "season": "Весна 2019"},
    ],
    "legends": [],
}


def seed(session: Session, empty: bool = False) -> None:
    session.add(ContentDoc(key="club", data=CLUB))
    session.add(ContentDoc(key="history", data=EMPTY_HISTORY if empty else HISTORY))
    if empty:
        session.flush()
        recompute(session)
        return
    season = Season(slug="2026-27", label="2026/27")
    li = Tournament(
        slug="liga-inzhenerov-osen-2026",
        name="Лига Инженеров · Осень 2026",
        short="Лига Инженеров",
        source="joinfootball",
        external_id="1066703",
        season=season,
        url="https://bauman_league.join.football/tournament/1066703",
    )
    lfl = Tournament(
        slug="lfl-2026-27",
        name="ЛФЛ 8×8 · 2026/27",
        short="ЛФЛ",
        source="lfl",
        external_id="e2e-lfl",
        season=season,
        url="https://lfl.ru/tournament-e2e",
    )
    players = [
        _player("egor-kucha", "Егор", "Куча", 1, "GK"),
        _player("fedor-meshkov", "Федор", "Мешков", 5, "DF"),
        _player("kirill-kolochkov", "Кирилл", "Колочков", 15, "DF"),
        _player(
            "aleksandr-korolev",
            "Александр",
            "Королев",
            10,
            "MF",
            nickname="Король",
            photo="/crest-white.png",  # лидеры сезона на главной — с фото
            is_captain=True,
            fact="Отдал 6 передач за пять туров.",
            faculty="ИУ7",
            foot="Правая",
            joined=2019,
        ),
        _player("konstantin-konstantinopolskiy", "Константин", "Константинопольский", 8, "MF"),
        _player("dmitriy-pisarev", "Дмитрий", "Писарев", 11, "FW", photo="/crest-white.png"),
    ]
    session.add_all([season, li, lfl, *players])
    session.flush()
    by = {p.slug: p for p in players}
    for slug, (pl, g, a) in {
        "egor-kucha": (3, 0, 0),
        "fedor-meshkov": (3, 1, 1),
        "kirill-kolochkov": (3, 2, 0),
        "aleksandr-korolev": (3, 2, 4),
        "konstantin-konstantinopolskiy": (2, 0, 1),
        "dmitriy-pisarev": (3, 3, 1),
    }.items():
        session.add(
            PlayerTournamentStats(
                player_id=by[slug].id, tournament_id=li.id, played=pl, goals=g, assists=a
            )
        )

    # ЛФЛ: в заявке двое (вкладка «ЛФЛ» на /team)
    for slug, (pl, g) in {"aleksandr-korolev": (1, 1), "dmitriy-pisarev": (1, 1)}.items():
        session.add(
            PlayerTournamentStats(player_id=by[slug].id, tournament_id=lfl.id, played=pl, goals=g)
        )

    def match(slug, day, home, opp, status, us=None, them=None, t=li, rnd=None):
        return Match(
            slug=slug,
            tournament_id=t.id,
            season_id=season.id,
            round=rnd,
            kickoff=datetime(*day, tzinfo=UTC) if day else None,
            home=home,
            venue_name="Металлург",
            venue_address="Москва, улица Новая Дорога, 11с1",
            opponent_name=opp,
            status=status,
            score_us=us,
            score_them=them,
            source=t.source,
            external_id=slug[:64],  # Match.external_id — String(64)
        )

    m1 = match(
        "2026-09-06-energiya", (2026, 9, 6, 17, 30), True, "Энергия", "finished", 3, 1, rnd="1 тур"
    )
    m1.events.extend(
        [
            MatchEvent(
                minute=12,
                type="goal",
                team="us",
                player_id=by["aleksandr-korolev"].id,
                assist_id=by["dmitriy-pisarev"].id,
            ),
            MatchEvent(minute=30, type="yellow", team="them", player_name="Сидоров Петр"),
            MatchEvent(minute=44, type="goal", team="them", player_name="Сидоров Петр"),
            MatchEvent(minute=51, type="goal", team="us", player_id=by["dmitriy-pisarev"].id),
            MatchEvent(minute=60, type="goal", team="us", player_id=by["kirill-kolochkov"].id),
        ]
    )
    m1.mvp_player_id = by["aleksandr-korolev"].id
    m1.report_news_slug = "pobeda-nad-energiey"
    m2 = match(
        "2026-09-20-dolgoprudnenskiy-politekh-imeni-ochen-dlinnogo-nazvaniya",
        (2026, 9, 20, 16, 0),
        False,
        "Долгопрудненский политех имени очень длинного названия",
        "finished",
        2,
        2,
        t=lfl,
        rnd="2 тур",
    )
    m3 = match(
        "2026-10-04-raskat", (2026, 10, 4, 18, 0), True, "Раскат", "finished", 0, 2, rnd="3 тур"
    )
    m4 = match(
        "2030-10-24-messiya", (2030, 10, 24, 18, 30), False, "Мессия", "scheduled", rnd="6 тур"
    )
    # дата на сайте лиги «Не задано» → на сайте «Дата уточняется»
    m5 = match("kvazar-5877228", None, False, "Квазар", "scheduled", rnd="Четвертьфинал")
    session.add_all([m1, m2, m3, m4, m5])
    teams = [
        "Раскат",
        "ФК ФН",
        "Реактор",
        "Bauman United",
        "Энергия",
        "Мессия",
        "Армада",
        "Поршень",
    ]
    for pos, team in enumerate(teams, start=1):
        session.add(
            StandingRow(
                tournament_id=li.id,
                pos=pos,
                team_name=team,
                played=3,
                won=max(0, 3 - pos // 3),
                drawn=0,
                lost=min(3, pos // 3),
                gf=10 - pos,
                ga=pos,
                pts=max(0, 9 - pos),
                is_us=team == "Bauman United",
                updated_at=datetime(2026, 10, 12, 9, 0, tzinfo=UTC),
            )
        )
    lfl_teams = ["Политех", "Bauman United", "Долгопрудненский политех", "Сокол", "Вымпел", "Титан"]
    for pos, team in enumerate(lfl_teams, start=1):
        session.add(
            StandingRow(
                tournament_id=lfl.id,
                pos=pos,
                team_name=team,
                played=1,
                won=1 if pos == 1 else 0,
                drawn=1 if pos in (2, 3) else 0,
                lost=0 if pos <= 3 else 1,
                gf=3,
                ga=2,
                pts=max(0, 7 - pos),
                is_us=team == "Bauman United",
                updated_at=datetime(2026, 10, 12, 9, 0, tzinfo=UTC),
            )
        )
    session.add_all(
        [
            News(
                slug="pobeda-nad-energiey",
                date=date(2026, 9, 7),
                tag="match",
                title="Победа над «Энергией» на старте",
                lead="3:1 в первом туре Лиги Инженеров.",
                body_md="## Как это было\n\nКоролев открыл счёт на **12-й** минуте.",
                match_slug="2026-09-06-energiya",
                featured=True,
            ),
            News(
                slug="nabor-v-komandu",
                date=date(2026, 9, 1),
                tag="club",
                title="Открыт набор в команду",
                body_md="Ищем вратаря и защитников.",
            ),
            News(
                slug="novyy-zashchitnik",
                date=date(2026, 9, 10),
                tag="transfer",
                title="У нас новый защитник",
                body_md="Добро пожаловать!",
            ),
            News(
                slug="post-tg-1",
                date=date(2026, 9, 12),
                tag="social",
                title="Тренировка перед Раскатом",
                body_md="Готовимся.",
                source_platform="telegram",
                source_url="https://t.me/baumanunited/1",
            ),
            News(
                slug="itogi-sentyabrya",
                date=date(2026, 9, 30),
                tag="club",
                title="Итоги сентября",
                body_md="Три матча, четыре очка.",
                # вертикальная картинка: на странице новости должна показаться целиком
                cover="/crest-black.png",
            ),
        ]
    )
    session.flush()
    recompute(session)


E2E_SUFFIXES = ("_e2e", "_e2e_empty")


def ensure_e2e_database(url: str) -> None:
    """Сид делает drop_all: разрешён только для БД с именем `*_e2e` / `*_e2e_empty`."""
    database = make_url(url).database or ""
    if not database.endswith(E2E_SUFFIXES):
        print(
            f"e2e_seed: отказ — БД {database!r} не похожа на e2e "
            f"(имя должно оканчиваться на {' или '.join(E2E_SUFFIXES)}); drop_all не выполнен.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main() -> None:
    url = sys.argv[1]
    ensure_e2e_database(url)
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, empty="--empty" in sys.argv)
        session.commit()


if __name__ == "__main__":
    main()
