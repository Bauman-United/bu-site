# План 1: платформа данных (core + worker + api)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Postgres-база, которую воркер наполняет из join.football и `content/`, плюс пересчёт статистики и read-only FastAPI для фронта.

**Architecture:** uv-workspace из трёх Python-пакетов: `bu_core` (модели, текст, склейка игроков, статистика), `bu_worker` (парсеры, синк контента, пайплайн, CLI и планировщик), `bu_api` (FastAPI). Парсеры — чистые функции над HTML; пайплайн пишет в БД в одной транзакции на источник; API только читает.

**Tech Stack:** Python 3.12, uv, SQLAlchemy 2 + psycopg 3, Alembic, pydantic 2, selectolax, httpx, python-frontmatter, PyYAML, FastAPI, APScheduler, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-10-15-bauman-united-site-design.md`

Это первый из серии планов: 1 — данные и API (этот), 2 — web MVP и техническое SEO, 3 — деплой, CI/CD, алерты, проверка lfl.ru, 4 — v2/v3 (фото с Я.Диска, статистика, история, форма заявки).

## Global Constraints

- Python `>=3.12`; все пакеты в одном uv-workspace, команды запускаются из корня репозитория через `uv run`.
- Даты рождения игроков не сохраняются и не возвращаются API.
- Пути join.football, закрытые robots.txt (`/matches`, `/player`, `/participants`), не запрашиваются. `/match/<id>`, `/tournament/...`, `/team/...` разрешены.
- Пауза ≥ 3 с между запросами к источнику, User-Agent `BaumanUnitedBot/1.0 (+<SITE_URL>)`.
- Время матчей хранится как `timestamptz`, источник отдаёт московское время (`Europe/Moscow`).
- Поля, заданные в `content/`, имеют приоритет над спарсенными.
- Наша команда на join.football: `team_id=1089660`, имя `Bauman United`. Текущий турнир: `1066703` (Лига Инженеров, осень 2026).
- Тесты используют локальный Postgres: `TEST_DATABASE_URL` (по умолчанию `postgresql+psycopg://localhost/bu_test`).

## Review Focus

1. Повторный запуск ингеста тех же данных не должен плодить игроков, матчи, события и строки таблицы (идемпотентность) — тест в Task 5.
2. Игрок, у которого в заявке нет номера или стоит «-» в статистике, должен импортироваться с `number=None` и нулями — тест в Task 3.
3. Матч, сыгранный в гостях: счёт и события «наши/соперника» должны быть развёрнуты правильно — тест в Task 5.
4. Пустой или урезанный ответ источника (сломанная вёрстка) не должен затирать данные — тест в Task 5 и Task 8.
5. Новость из `content/`, удалённая из репозитория, должна исчезнуть с сайта — тест в Task 6.

---

### Task 1: Каркас workspace, настройки, модели, миграция

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.env.example`, `conftest.py`
- Create: `core/pyproject.toml`, `core/bu_core/__init__.py`, `core/bu_core/settings.py`, `core/bu_core/db.py`, `core/bu_core/models.py`
- Create: `core/alembic.ini`, `core/migrations/env.py`, `core/migrations/script.py.mako`, `core/migrations/versions/0001_init.py` (генерируется)
- Create: `worker/pyproject.toml`, `worker/bu_worker/__init__.py`, `api/pyproject.toml`, `api/bu_api/__init__.py`
- Modify: `.gitignore`
- Test: `core/tests/test_models.py`

**Interfaces:**
- Produces: `bu_core.settings.get_settings() -> Settings`; `bu_core.db.make_engine(url: str | None = None) -> Engine`, `make_sessionmaker(engine) -> sessionmaker[Session]`; ORM-классы `Base, Season, Tournament, Player, PlayerSourceLink, Match, MatchEvent, MatchAppearance, PlayerTournamentStats, StandingRow, News, ContentDoc, PlayerSeasonStats, Computed, IngestRun`; pytest-фикстура `db: Session` (корневой `conftest.py`).

- [x] **Step 1: Корневой `pyproject.toml`**

```toml
[project]
name = "bu-site"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["bu-core", "bu-worker", "bu-api"]

[tool.uv]
package = false

[tool.uv.workspace]
members = ["core", "worker", "api"]

[tool.uv.sources]
bu-core = { workspace = true }
bu-worker = { workspace = true }
bu-api = { workspace = true }

[dependency-groups]
dev = ["pytest>=8.3", "ruff>=0.6", "mypy>=1.11", "types-PyYAML"]

[tool.pytest.ini_options]
testpaths = ["core/tests", "worker/tests", "api/tests"]
addopts = "--import-mode=importlib -q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

`.python-version`: `3.12`

- [x] **Step 2: Пакеты-члены**

`core/pyproject.toml`:
```toml
[project]
name = "bu-core"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "sqlalchemy>=2.0.30",
  "psycopg[binary]>=3.2",
  "alembic>=1.13",
  "pydantic>=2.8",
  "pydantic-settings>=2.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["bu_core"]
```

`worker/pyproject.toml` — то же с `name = "bu-worker"`, `packages = ["bu_worker"]` и зависимостями:
```toml
dependencies = [
  "bu-core",
  "httpx>=0.27",
  "selectolax>=0.3.21",
  "python-frontmatter>=1.1",
  "pyyaml>=6.0",
  "apscheduler>=3.10,<4",
]
[tool.uv.sources]
bu-core = { workspace = true }
```

`api/pyproject.toml` — `name = "bu-api"`, `packages = ["bu_api"]`:
```toml
dependencies = ["bu-core", "fastapi>=0.115", "uvicorn[standard]>=0.30", "httpx>=0.27"]
[tool.uv.sources]
bu-core = { workspace = true }
```

Пустые `__init__.py` в `core/bu_core`, `worker/bu_worker`, `api/bu_api`.

- [x] **Step 3: Настройки и подключение к БД**

`core/bu_core/settings.py`:
```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/bu_dev"
    site_url: str = "http://localhost:3000"
    our_team_names: list[str] = ["Bauman United", "Бауман Юнайтед"]
    joinfootball_base: str = "https://bauman_league.join.football"
    joinfootball_team_id: str = "1089660"
    joinfootball_tournament_ids: list[str] = ["1066703"]
    request_delay_s: float = 3.0
    content_dir: str = "content"
    snapshot_dir: str = "snapshots"
    snapshot_keep_days: int = 30
    revalidate_url: str | None = None
    revalidate_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`core/bu_core/db.py`:
```python
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from bu_core.settings import get_settings


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url, pool_pre_ping=True)


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
```

- [x] **Step 4: Модели**

`core/bu_core/models.py`:
```python
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Season(Base):
    __tablename__ = "season"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(16), unique=True)  # "2026-27"
    label: Mapped[str] = mapped_column(String(16))  # "2026/27"
    final_place: Mapped[str | None] = mapped_column(String(64))


class Tournament(Base):
    __tablename__ = "tournament"
    __table_args__ = (UniqueConstraint("source", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    short: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16), default="league")  # league | cup | friendly
    source: Mapped[str] = mapped_column(String(32))  # joinfootball | lfl | manual
    external_id: Mapped[str | None] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String(500))
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"))
    season: Mapped[Season] = relationship()


class Player(Base):
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    number: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(2))  # GK | DF | MF | FW
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    nickname: Mapped[str | None] = mapped_column(String(100))
    photo: Mapped[str | None] = mapped_column(String(500))
    fact: Mapped[str | None] = mapped_column(Text)
    foot: Mapped[str | None] = mapped_column(String(16))
    faculty: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str | None] = mapped_column(String(100))
    joined: Mapped[int | None] = mapped_column(Integer)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False)
    achievements: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    manual_fields: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class PlayerSourceLink(Base):
    __tablename__ = "player_source_link"
    __table_args__ = (UniqueConstraint("source", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(64))
    external_name: Mapped[str] = mapped_column(String(200))


class Match(Base):
    __tablename__ = "match"
    __table_args__ = (UniqueConstraint("source", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"))
    round: Mapped[str | None] = mapped_column(String(64))
    kickoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    home: Mapped[bool] = mapped_column(Boolean)
    venue_name: Mapped[str | None] = mapped_column(String(200))
    venue_address: Mapped[str | None] = mapped_column(String(300))
    opponent_name: Mapped[str] = mapped_column(String(200))
    opponent_logo: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16))  # scheduled | live | finished | cancelled
    score_us: Mapped[int | None] = mapped_column(Integer)
    score_them: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(500))
    mvp_player_id: Mapped[int | None] = mapped_column(ForeignKey("player.id", ondelete="SET NULL"))
    report_news_slug: Mapped[str | None] = mapped_column(String(160))
    stream_url: Mapped[str | None] = mapped_column(String(500))
    video_url: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    tournament: Mapped[Tournament] = relationship()
    season: Mapped[Season] = relationship()
    events: Mapped[list["MatchEvent"]] = relationship(
        cascade="all, delete-orphan", order_by="MatchEvent.minute"
    )


class MatchEvent(Base):
    __tablename__ = "match_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id", ondelete="CASCADE"))
    minute: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(16))  # goal | penalty | own_goal | yellow | red | sub
    team: Mapped[str] = mapped_column(String(4))  # us | them
    player_id: Mapped[int | None] = mapped_column(ForeignKey("player.id", ondelete="SET NULL"))
    player_name: Mapped[str | None] = mapped_column(String(200))
    assist_id: Mapped[int | None] = mapped_column(ForeignKey("player.id", ondelete="SET NULL"))
    assist_name: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(200))


class MatchAppearance(Base):
    __tablename__ = "match_appearance"
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id", ondelete="CASCADE"), primary_key=True
    )


class PlayerTournamentStats(Base):
    __tablename__ = "player_tournament_stats"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id", ondelete="CASCADE"), primary_key=True
    )
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournament.id", ondelete="CASCADE"), primary_key=True
    )
    played: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    yellow: Mapped[int] = mapped_column(Integer, default=0)
    red: Mapped[int] = mapped_column(Integer, default=0)


class StandingRow(Base):
    __tablename__ = "standing_row"
    __table_args__ = (UniqueConstraint("tournament_id", "team_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id", ondelete="CASCADE"))
    pos: Mapped[int] = mapped_column(Integer)
    team_name: Mapped[str] = mapped_column(String(200))
    team_logo: Mapped[str | None] = mapped_column(String(500))
    played: Mapped[int] = mapped_column(Integer)
    won: Mapped[int] = mapped_column(Integer)
    drawn: Mapped[int] = mapped_column(Integer)
    lost: Mapped[int] = mapped_column(Integer)
    gf: Mapped[int] = mapped_column(Integer)
    ga: Mapped[int] = mapped_column(Integer)
    pts: Mapped[int] = mapped_column(Integer)
    is_us: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    date: Mapped[date] = mapped_column(Date)
    tag: Mapped[str] = mapped_column(String(16))  # match | club | transfer | social
    title: Mapped[str] = mapped_column(String(300))
    lead: Mapped[str | None] = mapped_column(Text)
    body_md: Mapped[str] = mapped_column(Text, default="")
    cover: Mapped[str | None] = mapped_column(String(500))
    source_platform: Mapped[str | None] = mapped_column(String(16))
    source_url: Mapped[str | None] = mapped_column(String(500))
    match_slug: Mapped[str | None] = mapped_column(String(160))
    featured: Mapped[bool] = mapped_column(Boolean, default=False)


class ContentDoc(Base):
    __tablename__ = "content_doc"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # club | history
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id", ondelete="CASCADE"), primary_key=True
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), primary_key=True
    )
    played: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    yellow: Mapped[int] = mapped_column(Integer, default=0)
    red: Mapped[int] = mapped_column(Integer, default=0)
    mvp: Mapped[int] = mapped_column(Integer, default=0)


class Computed(Base):
    __tablename__ = "computed"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)


class IngestRun(Base):
    __tablename__ = "ingest_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))  # ok | rejected | error
    counts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
```

- [x] **Step 5: Тестовая БД — корневой `conftest.py`**

```python
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from bu_core.models import Base

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost/bu_test")


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            outer.rollback()
```

- [x] **Step 6: Падающий тест моделей**

`core/tests/test_models.py`:
```python
from datetime import UTC, datetime

from sqlalchemy import select

from bu_core.models import Match, MatchEvent, Player, Season, Tournament


def test_match_with_events_roundtrip(db):
    season = Season(slug="2026-27", label="2026/27")
    t = Tournament(
        slug="liga-inzhenerov-osen-2026",
        name="Лига Инженеров",
        short="ЛИ",
        source="joinfootball",
        external_id="1066703",
        season=season,
    )
    p = Player(slug="aleksandr-korolev", first_name="Александр", last_name="Королев")
    db.add_all([season, t, p])
    db.flush()
    m = Match(
        slug="2026-09-06-bauman-junior",
        tournament_id=t.id,
        season_id=season.id,
        kickoff=datetime(2026, 9, 6, 17, 30, tzinfo=UTC),
        home=True,
        opponent_name="Bauman Junior",
        status="finished",
        score_us=2,
        score_them=3,
        source="joinfootball",
        external_id="5848533",
    )
    m.events.append(MatchEvent(minute=22, type="goal", team="us", player_id=p.id))
    db.add(m)
    db.flush()

    loaded = db.scalars(select(Match).where(Match.slug == "2026-09-06-bauman-junior")).one()
    assert loaded.events[0].player_id == p.id
    assert loaded.tournament.season.slug == "2026-27"
    assert p.aliases == [] and p.manual_fields == []
```

Run: `createdb bu_test 2>/dev/null; createdb bu_dev 2>/dev/null; uv sync && uv run pytest core/tests/test_models.py`
Expected до Step 4: FAIL (ImportError). После: PASS.

- [x] **Step 7: Alembic и первая миграция**

`core/alembic.ini`:
```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .

[loggers]
keys = root
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic
[formatter_generic]
format = %(levelname)s %(message)s
```

`core/migrations/env.py`:
```python
from alembic import context

from bu_core.db import make_engine
from bu_core.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = make_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

`core/migrations/script.py.mako` — взять из `uv run alembic init /tmp/alembic-tpl` (файл `/tmp/alembic-tpl/script.py.mako`) без изменений.

Run:
```bash
uv run alembic -c core/alembic.ini revision --autogenerate -m init --rev-id 0001
uv run alembic -c core/alembic.ini upgrade head
uv run alembic -c core/alembic.ini check
```
Expected: `No new upgrade operations detected.`

- [x] **Step 8: `.env.example` и `.gitignore`**

`.env.example`:
```
DATABASE_URL=postgresql+psycopg://localhost/bu_dev
SITE_URL=http://localhost:3000
REVALIDATE_URL=http://localhost:3000/api/revalidate
REVALIDATE_SECRET=change-me
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

В `.gitignore` добавить: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `/snapshots/`, `node_modules/`.

- [x] **Step 9: Commit**

```bash
git add -A && git commit -m "feat(core): uv workspace, settings, models, initial migration"
```

---

### Task 2: Текстовые утилиты и склейка игроков

**Files:**
- Create: `core/bu_core/text.py`, `core/bu_core/matching.py`
- Test: `core/tests/test_text.py`, `core/tests/test_matching.py`

**Interfaces:**
- Produces: `normalize_name(value: str) -> str`; `slugify(value: str) -> str`; `split_last_first(full_name: str) -> tuple[str, str]` (возвращает `(first, last)`); `player_slug(first: str, last: str) -> str`; `PlayerName(id, first_name, last_name, aliases: tuple[str, ...] = ())`; `PlayerIndex(players).add(p)`, `.find(full_name) -> int | None` (бросает `AmbiguousMatchError` с `.name`, `.ids`).

- [x] **Step 1: Падающие тесты**

`core/tests/test_text.py`:
```python
import pytest

from bu_core.text import normalize_name, player_slug, slugify, split_last_first


def test_normalize_name():
    assert normalize_name("  Фёдор   ИВАНОВ ") == "федор иванов"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Королев Александр", "korolev-aleksandr"),
        ("Bauman Junior", "bauman-junior"),
        ("Интер/Атон", "inter-aton"),
        ("Щукин Юрий", "shchukin-yuriy"),
        ("ФК ФН", "fk-fn"),
    ],
)
def test_slugify(value, expected):
    assert slugify(value) == expected


def test_split_last_first():
    assert split_last_first("Королев Александр") == ("Александр", "Королев")
    assert split_last_first("Пеле") == ("", "Пеле")


def test_player_slug():
    assert player_slug("Александр", "Королев") == "aleksandr-korolev"
```

`core/tests/test_matching.py`:
```python
import pytest

from bu_core.matching import AmbiguousMatchError, PlayerIndex, PlayerName


def make_index():
    return PlayerIndex(
        [
            PlayerName(1, "Александр", "Королев"),
            PlayerName(2, "Кирилл", "Колочков", aliases=("Киря",)),
        ]
    )


def test_find_by_both_orders_and_yo():
    idx = make_index()
    assert idx.find("Королев Александр") == 1
    assert idx.find("александр  королёв") == 1


def test_find_by_alias_and_missing():
    idx = make_index()
    assert idx.find("Киря") == 2
    assert idx.find("Неизвестный Игрок") is None


def test_ambiguous():
    idx = make_index()
    idx.add(PlayerName(3, "Александр", "Королев"))
    with pytest.raises(AmbiguousMatchError) as err:
        idx.find("Королев Александр")
    assert err.value.ids == [1, 3]
```

Run: `uv run pytest core/tests/test_text.py core/tests/test_matching.py`
Expected: FAIL (ModuleNotFoundError).

- [x] **Step 2: Реализация**

`core/bu_core/text.py`:
```python
import re

_TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def normalize_name(value: str) -> str:
    return " ".join(value.lower().replace("ё", "е").split())


def slugify(value: str) -> str:
    latin = value.lower().translate(_TRANSLIT)
    return re.sub(r"[^a-z0-9]+", "-", latin).strip("-")


def split_last_first(full_name: str) -> tuple[str, str]:
    """Имя в источниках идёт как «Фамилия Имя». Возвращает (имя, фамилия)."""
    parts = full_name.split()
    if not parts:
        raise ValueError("empty name")
    return " ".join(parts[1:]), parts[0]


def player_slug(first_name: str, last_name: str) -> str:
    return slugify(f"{first_name} {last_name}")
```

`core/bu_core/matching.py`:
```python
from collections.abc import Iterable
from dataclasses import dataclass

from bu_core.text import normalize_name


@dataclass(frozen=True)
class PlayerName:
    id: int
    first_name: str
    last_name: str
    aliases: tuple[str, ...] = ()


class AmbiguousMatchError(Exception):
    def __init__(self, name: str, ids: list[int]):
        super().__init__(f"ambiguous player name {name!r}: candidates {ids}")
        self.name = name
        self.ids = ids


class PlayerIndex:
    """Поиск игрока по ФИО в любом порядке слов и по алиасам."""

    def __init__(self, players: Iterable[PlayerName] = ()):
        self._by_key: dict[str, set[int]] = {}
        for p in players:
            self.add(p)

    def add(self, p: PlayerName) -> None:
        keys = {
            normalize_name(f"{p.last_name} {p.first_name}"),
            normalize_name(f"{p.first_name} {p.last_name}"),
            *(normalize_name(a) for a in p.aliases),
        }
        for key in keys:
            if key:
                self._by_key.setdefault(key, set()).add(p.id)

    def find(self, full_name: str) -> int | None:
        ids = sorted(self._by_key.get(normalize_name(full_name), set()))
        if not ids:
            return None
        if len(ids) > 1:
            raise AmbiguousMatchError(full_name, ids)
        return ids[0]
```

- [x] **Step 3: Тесты зелёные**

Run: `uv run pytest core/tests/test_text.py core/tests/test_matching.py`
Expected: PASS.

- [x] **Step 4: Commit**

```bash
git add core && git commit -m "feat(core): name normalization, slugs, player index"
```

---

### Task 3: DTO и парсер join.football

**Files:**
- Create: `worker/bu_worker/dto.py`, `worker/bu_worker/sources/__init__.py`, `worker/bu_worker/sources/joinfootball/__init__.py`, `worker/bu_worker/sources/joinfootball/parse.py`
- Test: `worker/tests/test_joinfootball_parse.py` (фикстуры уже лежат в `worker/tests/fixtures/joinfootball/`: `application.html`, `calendar.html`, `tables.html`, `match_5848533.html`)

**Interfaces:**
- Produces (`bu_worker.dto`): `TournamentInfo(external_id, name, period_start: date, period_end: date, url)`, `ParsedPlayer(external_id, full_name, number: int|None, position: str|None, played, goals, assists, yellow, red)`, `CalendarEntry(external_id, kickoff: datetime, round: str|None, venue_name, venue_address, home_team_id, away_team_id, home_name, away_name, home_logo, away_logo, home_score: int|None, away_score: int|None)`, `ParsedEvent(minute, type, side: "home"|"away", player_name, assist_name, note)`, `MatchDetail(events: list[ParsedEvent], mvp_name: str|None, mvp_side: "home"|"away"|None)`, `ParsedStanding(pos, team_name, team_logo, played, won, drawn, lost, gf, ga, pts)`, `JoinFootballBundle(tournament, players, calendar, details: dict[str, MatchDetail], standings)`.
- Produces (`parse`): `parse_tournament_info(html, external_id, url) -> TournamentInfo`; `parse_application(html) -> list[ParsedPlayer]`; `parse_calendar(html, period_start, period_end) -> list[CalendarEntry]`; `parse_match(html) -> MatchDetail`; `parse_standings(html) -> list[ParsedStanding]`; `ParseError`.

- [x] **Step 1: DTO**

`worker/bu_worker/dto.py`:
```python
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Side = Literal["home", "away"]
EventType = Literal["goal", "penalty", "own_goal", "yellow", "red"]


class TournamentInfo(BaseModel):
    external_id: str
    name: str
    period_start: date
    period_end: date
    url: str


class ParsedPlayer(BaseModel):
    external_id: str
    full_name: str
    number: int | None
    position: str | None
    played: int
    goals: int
    assists: int
    yellow: int
    red: int


class CalendarEntry(BaseModel):
    external_id: str
    kickoff: datetime
    round: str | None
    venue_name: str | None
    venue_address: str | None
    home_team_id: str
    away_team_id: str
    home_name: str
    away_name: str
    home_logo: str | None
    away_logo: str | None
    home_score: int | None
    away_score: int | None


class ParsedEvent(BaseModel):
    minute: int
    type: EventType
    side: Side
    player_name: str | None
    assist_name: str | None = None
    note: str | None = None


class MatchDetail(BaseModel):
    events: list[ParsedEvent]
    mvp_name: str | None = None
    mvp_side: Side | None = None


class ParsedStanding(BaseModel):
    pos: int
    team_name: str
    team_logo: str | None
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    pts: int


class JoinFootballBundle(BaseModel):
    tournament: TournamentInfo
    players: list[ParsedPlayer]
    calendar: list[CalendarEntry]  # только матчи нашей команды
    details: dict[str, MatchDetail]  # external_id матча -> события
    standings: list[ParsedStanding]
```

- [x] **Step 2: Падающие тесты на реальных фикстурах**

`worker/tests/test_joinfootball_parse.py`:
```python
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from bu_worker.sources.joinfootball.parse import (
    ParseError,
    parse_application,
    parse_calendar,
    parse_match,
    parse_standings,
    parse_tournament_info,
)

FIX = Path(__file__).parent / "fixtures" / "joinfootball"
MSK = ZoneInfo("Europe/Moscow")


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_tournament_info():
    info = parse_tournament_info(read("calendar.html"), "1066703", "https://x/tournament/1066703")
    assert info.name == "Лига Инженеров · Осень 2026"
    assert info.period_start == date(2026, 9, 5)
    assert info.period_end == date(2026, 11, 22)


def test_application_players():
    players = parse_application(read("application.html"))
    assert len(players) == 25
    korolev = next(p for p in players if p.full_name == "Королев Александр")
    assert korolev.model_dump() == {
        "external_id": "2079261",
        "full_name": "Королев Александр",
        "number": 10,
        "position": "MF",
        "played": 5,
        "goals": 2,
        "assists": 6,
        "yellow": 0,
        "red": 0,
    }


def test_application_player_without_number_and_dashes():
    players = {p.full_name: p for p in parse_application(read("application.html"))}
    assert players["Алексеев Александр"].number is None
    assert players["Алексеев Александр"].position == "DF"
    assert players["Алексеев Александр"].played == 2
    trifonov = players["Трифонов Матвей"]
    assert (trifonov.played, trifonov.goals, trifonov.yellow) == (0, 0, 0)


def test_calendar_all_matches_and_ours():
    entries = parse_calendar(read("calendar.html"), date(2026, 9, 5), date(2026, 11, 22))
    assert len(entries) == 45
    ours = [e for e in entries if "1089660" in (e.home_team_id, e.away_team_id)]
    assert len(ours) == 9
    first = next(e for e in ours if e.external_id == "5848533")
    assert first.kickoff == datetime(2026, 9, 6, 20, 30, tzinfo=MSK)
    assert (first.home_name, first.away_name) == ("Bauman United", "Bauman Junior")
    assert (first.home_score, first.away_score) == (2, 3)
    assert first.round == "1 тур"
    assert first.venue_name == "Металлург"
    assert first.venue_address == "Металлург, Россия, Москва, улица Новая Дорога, 11с1"
    future = next(e for e in ours if e.external_id == "5922873")
    assert future.home_score is None and future.away_team_id == "1089660"


def test_match_events_and_mvp():
    detail = parse_match(read("match_5848533.html"))
    assert len(detail.events) == 7
    first = detail.events[0]
    assert (first.minute, first.type, first.side, first.player_name) == (
        19,
        "goal",
        "away",
        "Горевой Александр",
    )
    set_piece = next(e for e in detail.events if e.minute == 25)
    assert (set_piece.type, set_piece.side, set_piece.note) == ("goal", "home", "со стандарта")
    with_assist = next(e for e in detail.events if e.minute == 46)
    assert with_assist.assist_name == "Микульский Николай"
    yellow = next(e for e in detail.events if e.minute == 43)
    assert (yellow.type, yellow.side, yellow.player_name) == ("yellow", "home", "Заночуев Михаил")
    assert (detail.mvp_name, detail.mvp_side) == ("Горевой Александр", "away")


def test_standings():
    rows = parse_standings(read("tables.html"))
    assert len(rows) == 10
    us = next(r for r in rows if r.team_name == "Bauman United")
    assert (us.pos, us.played, us.won, us.drawn, us.lost, us.gf, us.ga, us.pts) == (
        6,
        5,
        2,
        0,
        3,
        17,
        19,
        6,
    )
    assert rows[0].pos == 1


def test_broken_html_raises():
    with pytest.raises(ParseError):
        parse_application("<html><body>maintenance</body></html>")
    with pytest.raises(ParseError):
        parse_standings("<html></html>")
```

Run: `uv run pytest worker/tests/test_joinfootball_parse.py`
Expected: FAIL (ModuleNotFoundError).

- [x] **Step 3: Реализация парсера**

`worker/bu_worker/sources/joinfootball/parse.py`:
```python
"""Чистые функции: HTML страниц join.football -> DTO. Сеть здесь не используется."""

import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from selectolax.parser import HTMLParser, Node

from bu_worker.dto import (
    CalendarEntry,
    MatchDetail,
    ParsedEvent,
    ParsedPlayer,
    ParsedStanding,
    Side,
    TournamentInfo,
)

MSK = ZoneInfo("Europe/Moscow")
MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
POSITIONS = {"Вр.": "GK", "Зщ.": "DF", "Пз.": "MF", "Нп.": "FW"}
_PERIOD = re.compile(r"(\d{1,2}) ([а-я]+) (\d{4}) - (\d{1,2}) ([а-я]+) (\d{4})")
_DAY = re.compile(r"(\d{1,2}) ([а-я]+)")
_SCORE = re.compile(r"(\d+)\s*[-:]\s*(\d+)")
_TEAM_ID = re.compile(r"team_id=(\d+)")
_LAST_ID = re.compile(r"/(\d+)(?:\?|$)")


class ParseError(Exception):
    pass


def _text(node: Node | None) -> str:
    return node.text(strip=True) if node is not None else ""


def _int(value: str) -> int:
    value = value.strip()
    return int(value) if value.isdigit() else 0


def _attr(node: Node | None, name: str) -> str | None:
    if node is None:
        return None
    return node.attributes.get(name)


def _date_in_period(day: int, month_name: str, start: date, end: date) -> date:
    month = MONTHS[month_name]
    for year in range(start.year, end.year + 1):
        candidate = date(year, month, day)
        if start <= candidate <= end:
            return candidate
    return date(start.year, month, day)


def parse_tournament_info(html: str, external_id: str, url: str) -> TournamentInfo:
    tree = HTMLParser(html)
    title = _text(tree.css_first(".blk-tournamentheader__title"))
    dates = _text(tree.css_first(".blk-tournamentheader__info-dates"))
    m = _PERIOD.search(dates)
    if not title or not m:
        raise ParseError("tournament header not found")
    start = date(int(m[3]), MONTHS[m[2]], int(m[1]))
    end = date(int(m[6]), MONTHS[m[5]], int(m[4]))
    name = " · ".join(part.strip() for part in title.split("|"))
    return TournamentInfo(
        external_id=external_id, name=name, period_start=start, period_end=end, url=url
    )


def parse_application(html: str) -> list[ParsedPlayer]:
    tree = HTMLParser(html)
    table = tree.css_first("table.blk-tteams__table")  # первая таблица — текущая заявка
    rows = table.css("tr.blk-tteams__row") if table is not None else []
    if not rows:
        raise ParseError("application table not found")
    players: list[ParsedPlayer] = []
    for row in rows:
        link = row.css_first("a.blk-tteams__player")
        href = _attr(link, "href") or ""
        id_match = _LAST_ID.search(href)
        name = _text(row.css_first(".blk-tteams__player-name"))
        if not id_match or not name:
            continue
        number_text = _text(row.css_first(".blk-tteams__cell--number"))
        stats = [_int(_text(cell)) for cell in row.css(".blk-tteams__cell--var")]
        stats += [0] * (5 - len(stats))
        players.append(
            ParsedPlayer(
                external_id=id_match[1],
                full_name=name,
                number=int(number_text) if number_text.isdigit() else None,
                position=POSITIONS.get(_text(row.css_first(".blk-tteams__cell--amplua"))),
                played=stats[0],
                goals=stats[1],
                assists=stats[2],
                yellow=stats[3],
                red=stats[4],
            )
        )
    if not players:
        raise ParseError("no players parsed")
    return players


def _team_side(item: Node, side: str) -> tuple[str, str, str | None]:
    team = item.css_first(f".blk-tcalendar__team--{side}")
    team_id_match = _TEAM_ID.search(_attr(team, "href") or "")
    name = _text(team.css_first(".blk-tcalendar__team-name")) if team is not None else ""
    logo = _attr(team.css_first("img"), "src") if team is not None else None
    return (team_id_match[1] if team_id_match else ""), name, logo


def parse_calendar(html: str, period_start: date, period_end: date) -> list[CalendarEntry]:
    tree = HTMLParser(html)
    entries: dict[str, CalendarEntry] = {}
    for unit in tree.css(".blk-tcalendar__unit"):
        day_match = _DAY.search(_text(unit.css_first(".blk-tcalendar__head-text")))
        if not day_match:
            continue
        day = _date_in_period(int(day_match[1]), day_match[2], period_start, period_end)
        for item in unit.css("li.blk-tcalendar__item"):
            score_link = item.css_first("a.blk-tcalendar__score")
            match_id = _LAST_ID.search(_attr(score_link, "href") or "")
            if not match_id:
                continue
            hh, mm = (_text(item.css_first(".blk-tcalendar__time")) or "00:00").split(":")
            place = item.css_first(".blk-tcalendar__place")
            score = _SCORE.search(_text(item.css_first(".blk-tcalendar__score-main")))
            home_id, home_name, home_logo = _team_side(item, "left")
            away_id, away_name, away_logo = _team_side(item, "right")
            entries[match_id[1]] = CalendarEntry(
                external_id=match_id[1],
                kickoff=datetime.combine(day, time(int(hh), int(mm)), tzinfo=MSK),
                round=_text(item.css_first(".blk-tcalendar__round")) or None,
                venue_name=_text(item.css_first(".blk-tcalendar__place-name")) or None,
                venue_address=_attr(place, "title"),
                home_team_id=home_id,
                away_team_id=away_id,
                home_name=home_name,
                away_name=away_name,
                home_logo=home_logo,
                away_logo=away_logo,
                home_score=int(score[1]) if score else None,
                away_score=int(score[2]) if score else None,
            )
    if not entries:
        raise ParseError("calendar is empty")
    return list(entries.values())


def _event_type(classes: list[str]) -> tuple[str, str | None] | None:
    if "goal" in classes:
        return "goal", None
    if "goal-standard" in classes:
        return "goal", "со стандарта"
    if "penalty" in classes or "goal-penalty" in classes:
        return "penalty", None
    if "autogoal" in classes or "own-goal" in classes:
        return "own_goal", None
    if "yellow-card" in classes:
        return "yellow", None
    if "red-card" in classes or "second-yellow-card" in classes:
        return "red", None
    return None


def parse_match(html: str) -> MatchDetail:
    tree = HTMLParser(html)
    if tree.css_first(".blk-matchheader") is None:
        raise ParseError("match header not found")
    events: list[ParsedEvent] = []
    for node in tree.css(".game-timeline__event"):
        classes = (_attr(node, "class") or "").split()
        kind = _event_type(classes)
        minute_text = (_attr(node, "data-time") or "").strip().rstrip("'").split("+")[0]
        if kind is None or not minute_text.isdigit():
            continue
        side: Side = "home" if "team1" in classes else "away"
        events.append(
            ParsedEvent(
                minute=int(minute_text),
                type=kind[0],
                side=side,  # type: ignore[arg-type]
                player_name=_attr(node, "data-player-first"),
                assist_name=_attr(node, "data-player-second"),
                note=kind[1],
            )
        )
    events.sort(key=lambda e: e.minute)

    mvp_name: str | None = None
    mvp_side: Side | None = None
    for index, unit in enumerate(tree.css(".blk-matchheader__unit")):
        best = unit.css_first(".blk-matchheader__best-name")
        if best is not None:
            mvp_name = _text(best)
            mvp_side = "home" if index == 0 else "away"
    return MatchDetail(events=events, mvp_name=mvp_name, mvp_side=mvp_side)


def parse_standings(html: str) -> list[ParsedStanding]:
    tree = HTMLParser(html)
    table = tree.css_first(".custom-table-table")
    if table is None:
        raise ParseError("standings table not found")
    rows: list[ParsedStanding] = []
    for line in table.css("li.custom-table__line"):
        values = [_text(cell) for cell in line.css(".custom-table__var")]
        pos = _text(line.css_first(".custom-table__number-wrapper"))
        if len(values) < 6 or not pos.isdigit():
            continue
        goals = _SCORE.search(values[4])
        rows.append(
            ParsedStanding(
                pos=int(pos),
                team_name=_text(line.css_first(".custom-table__team-name")),
                team_logo=_attr(line.css_first(".custom-table__team-img"), "src"),
                played=_int(values[0]),
                won=_int(values[1]),
                drawn=_int(values[2]),
                lost=_int(values[3]),
                gf=int(goals[1]) if goals else 0,
                ga=int(goals[2]) if goals else 0,
                pts=_int(values[5]),
            )
        )
    if not rows:
        raise ParseError("standings are empty")
    return rows
```

Пустые `worker/bu_worker/sources/__init__.py` и `worker/bu_worker/sources/joinfootball/__init__.py`.

- [x] **Step 4: Тесты зелёные**

Run: `uv run pytest worker/tests/test_joinfootball_parse.py -v`
Expected: PASS. Если какой-то селектор не совпал с фикстурой — поправить селектор по фактическому HTML фикстуры (не ослабляя ассерты теста).

- [x] **Step 5: Commit**

```bash
git add worker && git commit -m "feat(worker): join.football HTML parsers with real fixtures"
```

---

### Task 4: Загрузчик `content/` и стартовый контент

**Files:**
- Create: `worker/bu_worker/sources/content.py`
- Create: `content/club.yaml`, `content/history.yaml`, `content/tournaments.yaml`, `content/news/2026-09-06-start-ligi-inzhenerov.md`, `content/players/.gitkeep`, `content/matches/.gitkeep`
- Test: `worker/tests/test_content_load.py`

**Interfaces:**
- Produces: `load_content(root: Path) -> ContentBundle`; `ContentError(path, message)`; модели `ClubDoc` (extra=allow, обязательные `name`, `primary_tournament: str | None`), `PlayerContent`, `NewsContent(slug, date, tag, title, lead, cover, source, match, featured, body)`, `TournamentContent(slug, name, short, kind, season)`, `MatchContent`, `ContentBundle(club: dict, history: dict, tournaments, players: dict[str, PlayerContent], news: list[NewsContent], matches: dict[str, MatchContent])`.

- [x] **Step 1: Падающие тесты**

`worker/tests/test_content_load.py`:
```python
from pathlib import Path

import pytest

from bu_worker.sources.content import ContentError, load_content

REPO_CONTENT = Path(__file__).resolve().parents[2] / "content"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def minimal(root: Path) -> None:
    write(root, "club.yaml", "name: Бауман Юнайтед\nprimary_tournament: null\n")
    write(root, "history.yaml", "timeline: []\ntrophies: []\nlegends: []\n")
    write(root, "tournaments.yaml", "[]\n")


def test_repo_content_is_valid():
    bundle = load_content(REPO_CONTENT)
    assert bundle.club["name"] == "Бауман Юнайтед"
    assert bundle.news


def test_player_and_news(tmp_path):
    minimal(tmp_path)
    write(
        tmp_path,
        "players/aleksandr-korolev.yaml",
        "first_name: Александр\nlast_name: Королев\nnickname: Король\naliases: [Саня]\n",
    )
    write(
        tmp_path,
        "news/hello.md",
        "---\ndate: 2026-09-06\ntag: match\ntitle: Привет\n---\nТекст **жирный**\n",
    )
    bundle = load_content(tmp_path)
    player = bundle.players["aleksandr-korolev"]
    assert player.nickname == "Король" and player.aliases == ["Саня"]
    assert player.provided_fields() == {"nickname"}
    assert bundle.news[0].slug == "hello" and bundle.news[0].body.startswith("Текст")


def test_invalid_tag_reports_file(tmp_path):
    minimal(tmp_path)
    write(tmp_path, "news/bad.md", "---\ndate: 2026-09-06\ntag: gossip\ntitle: X\n---\n")
    with pytest.raises(ContentError) as err:
        load_content(tmp_path)
    assert "news/bad.md" in str(err.value) and "tag" in str(err.value)


def test_manual_match(tmp_path):
    minimal(tmp_path)
    write(
        tmp_path,
        "tournaments.yaml",
        "- {slug: lfl-2026-27, name: ЛФЛ 8×8, short: ЛФЛ, kind: league, season: 2026-27}\n",
    )
    write(
        tmp_path,
        "matches/2026-10-11-energiya.yaml",
        """
tournament: lfl-2026-27
kickoff: 2026-10-11T14:00:00+03:00
home: true
opponent: {name: Энергия}
status: finished
score: {us: 3, them: 1}
squad: [aleksandr-korolev]
events:
  - {minute: 12, type: goal, team: us, player: aleksandr-korolev}
""",
    )
    match = load_content(tmp_path).matches["2026-10-11-energiya"]
    assert match.score is not None and match.score.us == 3
    assert match.events[0].player == "aleksandr-korolev"
```

Run: `uv run pytest worker/tests/test_content_load.py`
Expected: FAIL.

- [x] **Step 2: Реализация**

`worker/bu_worker/sources/content.py`:
```python
"""Загрузка и валидация ручного контента из каталога content/."""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import frontmatter
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError


class ContentError(Exception):
    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Achievement(_Strict):
    title: str
    subtitle: str | None = None
    icon: Literal["cup", "medal", "star"] = "star"


class PlayerContent(_Strict):
    first_name: str | None = None
    last_name: str | None = None
    number: int | None = None
    position: Literal["GK", "DF", "MF", "FW"] | None = None
    active: bool | None = None
    nickname: str | None = None
    photo: str | None = None
    fact: str | None = None
    foot: str | None = None
    faculty: str | None = None
    role: str | None = None
    joined: int | None = None
    is_captain: bool | None = None
    achievements: list[Achievement] | None = None
    aliases: list[str] = []

    def provided_fields(self) -> set[str]:
        """Поля, явно заданные в YAML и перекрывающие данные парсеров."""
        skip = {"first_name", "last_name", "aliases"}
        return {name for name in self.model_fields_set if name not in skip}


class NewsSource(_Strict):
    platform: Literal["telegram", "vk", "youtube"]
    url: str


class NewsContent(_Strict):
    slug: str
    date: date
    tag: Literal["match", "club", "transfer", "social"]
    title: str
    lead: str | None = None
    cover: str | None = None
    source: NewsSource | None = None
    match: str | None = None
    featured: bool = False
    body: str = ""


class TournamentContent(_Strict):
    slug: str
    name: str
    short: str
    kind: Literal["league", "cup", "friendly"] = "league"
    season: str
    url: str | None = None


class Venue(_Strict):
    name: str
    address: str | None = None


class Opponent(_Strict):
    name: str
    logo: str | None = None


class Score(_Strict):
    us: int
    them: int


class EventContent(_Strict):
    minute: int
    type: Literal["goal", "penalty", "own_goal", "yellow", "red", "sub"]
    team: Literal["us", "them"]
    player: str | None = None  # slug для нас, имя для соперника
    assist: str | None = None
    note: str | None = None


class MatchContent(_Strict):
    tournament: str | None = None  # обязателен для ручного матча, не нужен для дополнения
    round: str | None = None
    kickoff: datetime | None = None
    home: bool | None = None
    venue: Venue | None = None
    opponent: Opponent | None = None
    status: Literal["scheduled", "live", "finished", "cancelled"] | None = None
    score: Score | None = None
    squad: list[str] = []
    events: list[EventContent] = []
    mvp: str | None = None
    report_news: str | None = None
    stream_url: str | None = None
    video_url: str | None = None


class ContentBundle(BaseModel):
    club: dict[str, Any]
    history: dict[str, Any]
    tournaments: list[TournamentContent]
    players: dict[str, PlayerContent]
    news: list[NewsContent]
    matches: dict[str, MatchContent]


def _yaml(path: Path, root: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContentError(str(path.relative_to(root)), f"invalid YAML: {exc}") from exc


def _validate[T: BaseModel](model: type[T], data: Any, path: Path, root: Path) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ContentError(str(path.relative_to(root)), problems) from exc


def load_content(root: Path) -> ContentBundle:
    club = _yaml(root / "club.yaml", root) or {}
    if "name" not in club:
        raise ContentError("club.yaml", "name: field required")
    history = _yaml(root / "history.yaml", root) or {}
    tournaments = [
        _validate(TournamentContent, item, root / "tournaments.yaml", root)
        for item in (_yaml(root / "tournaments.yaml", root) or [])
    ]
    players = {
        path.stem: _validate(PlayerContent, _yaml(path, root) or {}, path, root)
        for path in sorted((root / "players").glob("*.yaml"))
    }
    news: list[NewsContent] = []
    for path in sorted((root / "news").glob("*.md")):
        post = frontmatter.load(path)
        data = {**post.metadata, "slug": path.stem, "body": post.content}
        news.append(_validate(NewsContent, data, path, root))
    matches = {
        path.stem: _validate(MatchContent, _yaml(path, root) or {}, path, root)
        for path in sorted((root / "matches").glob("*.yaml"))
    }
    return ContentBundle(
        club=club,
        history=history,
        tournaments=tournaments,
        players=players,
        news=news,
        matches=matches,
    )
```

- [x] **Step 3: Стартовый контент**

`content/club.yaml`:
```yaml
name: Бауман Юнайтед
name_en: Bauman United
founded: null
city: Москва
university: МГТУ им. Н. Э. Баумана
format: 8x8
default_formation: 3-3-1
primary_tournament: null   # slug турнира для мини-таблицы на главной; null — первый турнир текущего сезона
socials:
  telegram: null
  vk: null
  youtube: null
  lfl: https://lfl.ru/club14270
  joinfootball: https://bauman_league.join.football/tournament/1066703/teams/application?team_id=1089660
contacts:
  captain_name: null
  captain_telegram: null
  email: null
training:
  days: null
  time: null
  place: null
  map_url: null
looking_for: []
player_of_month: null
```

`content/history.yaml`:
```yaml
timeline: []
trophies: []
legends: []
```

`content/tournaments.yaml`:
```yaml
[]
```

`content/news/2026-09-06-start-ligi-inzhenerov.md`:
```markdown
---
date: 2026-09-06
tag: match
title: Стартовали в Лиге Инженеров
lead: Первый тур осеннего сезона Bauman League — 2:3 против Bauman Junior.
match: 2026-09-06-bauman-junior
---
Осенний сезон Лиги Инженеров Бауманской футбольной лиги открыт. В первом туре «Бауман Юнайтед» уступил Bauman Junior со счётом 2:3. Голы забили Александр Королев и Кирилл Колочков.
```

- [x] **Step 4: Тесты зелёные**

Run: `uv run pytest worker/tests/test_content_load.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add worker content && git commit -m "feat(worker): content/ loader with validation and seed content"
```

---

### Task 5: Пайплайн ингеста join.football

**Files:**
- Create: `worker/bu_worker/pipeline/__init__.py`, `worker/bu_worker/pipeline/common.py`, `worker/bu_worker/pipeline/joinfootball.py`
- Test: `worker/tests/test_pipeline_joinfootball.py`

**Interfaces:**
- Consumes: `JoinFootballBundle` (Task 3); `PlayerIndex`, `PlayerName`, `AmbiguousMatchError`, `slugify`, `split_last_first`, `player_slug` (Task 2); модели (Task 1).
- Produces:
  - `common.season_slug_for(d: date) -> str` (июль и позже → `"2026-27"`, иначе `"2025-26"`); `common.ensure_season(session, slug) -> Season`; `common.unique_slug(session, model, base: str, exclude_id: int | None = None) -> str`; `common.player_index(session) -> PlayerIndex`; `common.IngestResult(counts: dict[str, int], warnings: list[str], tags: set[str])`.
  - `joinfootball.SanityError`; `joinfootball.sanity_check(session, source_key: str, bundle) -> None`; `joinfootball.ingest(session, bundle, our_team_id: str, our_names: list[str]) -> IngestResult`. Источник в `PlayerSourceLink.source`/`Match.source`/`Tournament.source` — `"joinfootball"`; ключ для `IngestRun.source` — `f"joinfootball:{tournament.external_id}"`.

- [ ] **Step 1: Падающие тесты**

`worker/tests/test_pipeline_joinfootball.py`:
```python
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from bu_core.models import (
    IngestRun,
    Match,
    MatchEvent,
    Player,
    PlayerTournamentStats,
    StandingRow,
)
from bu_worker.dto import JoinFootballBundle
from bu_worker.pipeline.joinfootball import SanityError, ingest, sanity_check
from bu_worker.sources.joinfootball.parse import (
    parse_application,
    parse_calendar,
    parse_match,
    parse_standings,
    parse_tournament_info,
)

FIX = Path(__file__).parent / "fixtures" / "joinfootball"
TEAM = "1089660"
NAMES = ["Bauman United"]


def bundle() -> JoinFootballBundle:
    read = lambda n: (FIX / n).read_text(encoding="utf-8")  # noqa: E731
    info = parse_tournament_info(read("calendar.html"), "1066703", "https://x/tournament/1066703")
    calendar = [
        e
        for e in parse_calendar(read("calendar.html"), info.period_start, info.period_end)
        if TEAM in (e.home_team_id, e.away_team_id)
    ]
    return JoinFootballBundle(
        tournament=info,
        players=parse_application(read("application.html")),
        calendar=calendar,
        details={"5848533": parse_match(read("match_5848533.html"))},
        standings=parse_standings(read("tables.html")),
    )


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_ingest_creates_everything(db):
    result = ingest(db, bundle(), TEAM, NAMES)
    assert count(db, Player) == 25
    assert count(db, Match) == 9
    assert count(db, StandingRow) == 10
    assert result.counts == {"players": 25, "matches": 9, "standings": 10}
    assert "matches" in result.tags and "player:aleksandr-korolev" in result.tags

    m = db.scalars(select(Match).where(Match.external_id == "5848533")).one()
    assert m.slug == "2026-09-06-bauman-junior"
    assert (m.home, m.score_us, m.score_them, m.status) == (True, 2, 3, "finished")
    assert m.tournament.season.slug == "2026-27"
    ours = [e for e in m.events if e.team == "us"]
    assert {e.player_name for e in ours if e.type == "goal"} == {
        "Королев Александр",
        "Колочков Кирилл",
    }
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    assert any(e.player_id == korolev.id for e in ours)
    assert m.mvp_player_id is None  # MVP матча — игрок соперника

    stats = db.get(PlayerTournamentStats, (korolev.id, m.tournament_id))
    assert (stats.played, stats.goals, stats.assists) == (5, 2, 6)
    us_row = db.scalars(select(StandingRow).where(StandingRow.is_us)).one()
    assert us_row.pos == 6


def test_ingest_is_idempotent(db):
    ingest(db, bundle(), TEAM, NAMES)
    ingest(db, bundle(), TEAM, NAMES)
    assert count(db, Player) == 25
    assert count(db, Match) == 9
    assert count(db, MatchEvent) == 7
    assert count(db, StandingRow) == 10


def test_away_match_is_mirrored(db):
    ingest(db, bundle(), TEAM, NAMES)
    away = db.scalars(select(Match).where(Match.external_id == "5922873")).one()
    assert away.home is False
    assert away.opponent_name == "Мессия"
    assert away.status == "scheduled" and away.score_us is None


def test_manual_fields_win(db):
    ingest(db, bundle(), TEAM, NAMES)
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    korolev.number = 7
    korolev.manual_fields = ["number"]
    db.flush()
    ingest(db, bundle(), TEAM, NAMES)
    db.refresh(korolev)
    assert korolev.number == 7


def test_sanity_rejects_shrunk_data(db):
    good = bundle()
    db.add(
        IngestRun(
            source="joinfootball:1066703",
            started_at=datetime.now(UTC),
            status="ok",
            counts={"players": 25, "matches": 9, "standings": 10},
        )
    )
    db.flush()
    sanity_check(db, "joinfootball:1066703", good)  # не бросает
    shrunk = good.model_copy(update={"players": good.players[:5]})
    with pytest.raises(SanityError):
        sanity_check(db, "joinfootball:1066703", shrunk)
    empty = good.model_copy(update={"standings": []})
    with pytest.raises(SanityError):
        sanity_check(db, "joinfootball:1066703", empty)
```

Run: `uv run pytest worker/tests/test_pipeline_joinfootball.py`
Expected: FAIL.

- [ ] **Step 2: Общие функции пайплайна**

`worker/bu_worker/pipeline/common.py`:
```python
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_core.matching import PlayerIndex, PlayerName
from bu_core.models import Player, Season


@dataclass
class IngestResult:
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)


def season_slug_for(d: date) -> str:
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def ensure_season(session: Session, slug: str) -> Season:
    season = session.scalars(select(Season).where(Season.slug == slug)).one_or_none()
    if season is None:
        start, end = slug.split("-")
        season = Season(slug=slug, label=f"{start}/{end}")
        session.add(season)
        session.flush()
    return season


def unique_slug(session: Session, model: Any, base: str, exclude_id: int | None = None) -> str:
    slug, n = base, 2
    while True:
        existing = session.scalars(select(model).where(model.slug == slug)).one_or_none()
        if existing is None or existing.id == exclude_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


def player_index(session: Session) -> PlayerIndex:
    return PlayerIndex(
        PlayerName(p.id, p.first_name, p.last_name, tuple(p.aliases or ()))
        for p in session.scalars(select(Player))
    )
```

Пустой `worker/bu_worker/pipeline/__init__.py`.

- [ ] **Step 3: Ингест join.football**

`worker/bu_worker/pipeline/joinfootball.py`:
```python
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bu_core.matching import AmbiguousMatchError, PlayerIndex, PlayerName
from bu_core.models import (
    IngestRun,
    Match,
    MatchEvent,
    Player,
    PlayerSourceLink,
    PlayerTournamentStats,
    StandingRow,
    Tournament,
)
from bu_core.text import player_slug, slugify, split_last_first
from bu_worker.dto import CalendarEntry, JoinFootballBundle, ParsedPlayer
from bu_worker.pipeline.common import (
    IngestResult,
    ensure_season,
    player_index,
    season_slug_for,
    unique_slug,
)

SOURCE = "joinfootball"
MIN_RATIO = 0.5


class SanityError(Exception):
    pass


def _counts(bundle: JoinFootballBundle) -> dict[str, int]:
    return {
        "players": len(bundle.players),
        "matches": len(bundle.calendar),
        "standings": len(bundle.standings),
    }


def sanity_check(session: Session, source_key: str, bundle: JoinFootballBundle) -> None:
    new = _counts(bundle)
    previous = session.scalars(
        select(IngestRun)
        .where(IngestRun.source == source_key, IngestRun.status == "ok")
        .order_by(IngestRun.started_at.desc())
        .limit(1)
    ).one_or_none()
    for key, value in new.items():
        if value == 0:
            raise SanityError(f"{key}: source returned 0 items")
        before = (previous.counts or {}).get(key, 0) if previous else 0
        if before and value < before * MIN_RATIO:
            raise SanityError(f"{key}: dropped from {before} to {value}")


def _upsert_tournament(session: Session, bundle: JoinFootballBundle) -> Tournament:
    info = bundle.tournament
    season = ensure_season(session, season_slug_for(info.period_start))
    tournament = session.scalars(
        select(Tournament).where(
            Tournament.source == SOURCE, Tournament.external_id == info.external_id
        )
    ).one_or_none()
    if tournament is None:
        tournament = Tournament(
            source=SOURCE,
            external_id=info.external_id,
            slug=unique_slug(session, Tournament, slugify(info.name)),
            short=info.name.split(" · ")[0],
            kind="league",
        )
        session.add(tournament)
    tournament.name = info.name
    tournament.url = info.url
    tournament.season_id = season.id
    session.flush()
    return tournament


def _resolve_player(
    session: Session, index: PlayerIndex, parsed: ParsedPlayer, warnings: list[str]
) -> Player | None:
    link = session.scalars(
        select(PlayerSourceLink).where(
            PlayerSourceLink.source == SOURCE,
            PlayerSourceLink.external_id == parsed.external_id,
        )
    ).one_or_none()
    if link is not None:
        return session.get(Player, link.player_id)
    try:
        player_id = index.find(parsed.full_name)
    except AmbiguousMatchError as exc:
        warnings.append(str(exc))
        return None
    if player_id is not None:
        player = session.get(Player, player_id)
    else:
        first, last = split_last_first(parsed.full_name)
        player = Player(
            first_name=first,
            last_name=last,
            slug=unique_slug(session, Player, player_slug(first, last)),
            aliases=[],
            manual_fields=[],
            achievements=[],
        )
        session.add(player)
        session.flush()
        index.add(PlayerName(player.id, first, last))
    session.add(
        PlayerSourceLink(
            player_id=player.id,
            source=SOURCE,
            external_id=parsed.external_id,
            external_name=parsed.full_name,
        )
    )
    return player


def _ingest_players(
    session: Session, bundle: JoinFootballBundle, tournament: Tournament, result: IngestResult
) -> PlayerIndex:
    index = player_index(session)
    for parsed in bundle.players:
        player = _resolve_player(session, index, parsed, result.warnings)
        if player is None:
            continue
        manual = set(player.manual_fields or [])
        if "number" not in manual:
            player.number = parsed.number
        if "position" not in manual and parsed.position:
            player.position = parsed.position
        if "active" not in manual:
            player.active = True
        stats = session.get(PlayerTournamentStats, (player.id, tournament.id))
        if stats is None:
            stats = PlayerTournamentStats(player_id=player.id, tournament_id=tournament.id)
            session.add(stats)
        stats.played, stats.goals, stats.assists = parsed.played, parsed.goals, parsed.assists
        stats.yellow, stats.red = parsed.yellow, parsed.red
        result.tags.add(f"player:{player.slug}")
    session.flush()
    return index


def _find_in_index(index: PlayerIndex, name: str | None, warnings: list[str]) -> int | None:
    if not name:
        return None
    try:
        return index.find(name)
    except AmbiguousMatchError as exc:
        warnings.append(str(exc))
        return None


def _ingest_match(
    session: Session,
    entry: CalendarEntry,
    bundle: JoinFootballBundle,
    tournament: Tournament,
    our_team_id: str,
    index: PlayerIndex,
    result: IngestResult,
) -> None:
    home = entry.home_team_id == our_team_id
    opponent = entry.away_name if home else entry.home_name
    match = session.scalars(
        select(Match).where(Match.source == SOURCE, Match.external_id == entry.external_id)
    ).one_or_none()
    if match is None:
        base = f"{entry.kickoff.date().isoformat()}-{slugify(opponent)}"
        match = Match(
            source=SOURCE, external_id=entry.external_id, slug=unique_slug(session, Match, base)
        )
        session.add(match)
    match.tournament_id = tournament.id
    match.season_id = tournament.season_id
    match.round = entry.round
    match.kickoff = entry.kickoff
    match.home = home
    match.venue_name = entry.venue_name
    match.venue_address = entry.venue_address
    match.opponent_name = opponent
    match.opponent_logo = entry.away_logo if home else entry.home_logo
    match.source_url = f"{bundle.tournament.url.split('/tournament/')[0]}/match/{entry.external_id}"
    finished = entry.home_score is not None and entry.away_score is not None
    if finished:
        match.score_us = entry.home_score if home else entry.away_score
        match.score_them = entry.away_score if home else entry.home_score
        match.status = "finished"
    else:
        match.score_us = match.score_them = None
        match.status = match.status if match.status in {"live", "cancelled"} else "scheduled"

    detail = bundle.details.get(entry.external_id)
    if detail is not None:
        our_side = "home" if home else "away"
        match.events.clear()
        session.flush()
        for ev in detail.events:
            is_us = ev.side == our_side
            match.events.append(
                MatchEvent(
                    minute=ev.minute,
                    type=ev.type,
                    team="us" if is_us else "them",
                    player_name=ev.player_name,
                    assist_name=ev.assist_name,
                    note=ev.note,
                    player_id=_find_in_index(index, ev.player_name, result.warnings)
                    if is_us
                    else None,
                    assist_id=_find_in_index(index, ev.assist_name, result.warnings)
                    if is_us
                    else None,
                )
            )
        match.mvp_player_id = (
            _find_in_index(index, detail.mvp_name, result.warnings)
            if detail.mvp_side == our_side
            else None
        )
    session.flush()
    result.tags.add(f"match:{match.slug}")


def _ingest_standings(
    session: Session, bundle: JoinFootballBundle, tournament: Tournament, our_names: list[str]
) -> None:
    session.execute(delete(StandingRow).where(StandingRow.tournament_id == tournament.id))
    now = datetime.now(UTC)
    names = {n.lower() for n in our_names}
    for row in bundle.standings:
        session.add(
            StandingRow(
                tournament_id=tournament.id,
                updated_at=now,
                is_us=row.team_name.lower() in names,
                **row.model_dump(),
            )
        )
    session.flush()


def ingest(
    session: Session, bundle: JoinFootballBundle, our_team_id: str, our_names: list[str]
) -> IngestResult:
    result = IngestResult(counts=_counts(bundle))
    tournament = _upsert_tournament(session, bundle)
    index = _ingest_players(session, bundle, tournament, result)
    for entry in bundle.calendar:
        _ingest_match(session, entry, bundle, tournament, our_team_id, index, result)
    _ingest_standings(session, bundle, tournament, our_names)
    result.tags |= {"matches", "players", "standings", "home", "stats"}
    return result
```

- [ ] **Step 4: Тесты зелёные**

Run: `uv run pytest worker/tests/test_pipeline_joinfootball.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker && git commit -m "feat(worker): join.football ingest pipeline with sanity check"
```

---

### Task 6: Синк `content/` в БД

**Files:**
- Create: `worker/bu_worker/pipeline/content.py`
- Test: `worker/tests/test_pipeline_content.py`

**Interfaces:**
- Consumes: `ContentBundle` и модели контента (Task 4); `common.*` (Task 5).
- Produces: `sync_content(session, bundle: ContentBundle) -> IngestResult`.

Правила: `club`/`history` → `ContentDoc`; турниры из `tournaments.yaml` → `Tournament(source="manual")`; игрок из YAML ищется по slug, затем по ФИО, иначе создаётся; заданные поля пишутся и попадают в `manual_fields`; новости — полная синхронизация (удалённые из репо удаляются из БД); матч из `matches/<slug>.yaml`: если матч с таким slug уже есть — дополняются `report_news`, `stream_url`, `video_url`, `mvp`, а события — только если у матча их нет; иначе создаётся ручной матч (`source="manual"`, нужны `tournament`, `kickoff`, `home`, `opponent`, `status`).

- [ ] **Step 1: Падающие тесты**

`worker/tests/test_pipeline_content.py`:
```python
from datetime import date

from sqlalchemy import select

from bu_core.models import ContentDoc, Match, MatchAppearance, News, Player
from bu_worker.pipeline.content import sync_content
from bu_worker.sources.content import (
    ContentBundle,
    MatchContent,
    NewsContent,
    PlayerContent,
    TournamentContent,
)


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
    t = TournamentContent(slug="lfl-2026-27", name="ЛФЛ 8×8", short="ЛФЛ", season="2026-27")
    m = MatchContent.model_validate(
        {
            "tournament": "lfl-2026-27",
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
```

Run: `uv run pytest worker/tests/test_pipeline_content.py`
Expected: FAIL.

- [ ] **Step 2: Реализация**

`worker/bu_worker/pipeline/content.py`:
```python
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bu_core.models import (
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    News,
    Player,
    Tournament,
)
from bu_worker.pipeline.common import IngestResult, ensure_season, player_index
from bu_worker.sources.content import ContentBundle, MatchContent, PlayerContent


def _set_doc(session: Session, key: str, data: dict) -> None:
    doc = session.get(ContentDoc, key)
    if doc is None:
        session.add(ContentDoc(key=key, data=data))
    else:
        doc.data = data


def _sync_player(session: Session, slug: str, content: PlayerContent) -> Player:
    player = session.scalars(select(Player).where(Player.slug == slug)).one_or_none()
    if player is None and content.first_name and content.last_name:
        player_id = player_index(session).find(f"{content.last_name} {content.first_name}")
        player = session.get(Player, player_id) if player_id else None
    if player is None:
        player = Player(
            slug=slug,
            first_name=content.first_name or "",
            last_name=content.last_name or slug,
            aliases=[],
            manual_fields=[],
            achievements=[],
        )
        session.add(player)
    if content.first_name:
        player.first_name = content.first_name
    if content.last_name:
        player.last_name = content.last_name
    player.aliases = list(content.aliases)
    provided = content.provided_fields()
    for field in provided:
        value = getattr(content, field)
        if field == "achievements":
            value = [a.model_dump() for a in value or []]
        setattr(player, field, value)
    player.manual_fields = sorted(provided)
    session.flush()
    return player


def _player_id_by_slug(session: Session, slug: str | None) -> int | None:
    if not slug:
        return None
    return session.scalars(select(Player.id).where(Player.slug == slug)).one_or_none()


def _events(session: Session, content: MatchContent) -> list[MatchEvent]:
    events = []
    for ev in content.events:
        is_us = ev.team == "us"
        events.append(
            MatchEvent(
                minute=ev.minute,
                type=ev.type,
                team=ev.team,
                note=ev.note,
                player_id=_player_id_by_slug(session, ev.player) if is_us else None,
                player_name=None if is_us else ev.player,
                assist_id=_player_id_by_slug(session, ev.assist) if is_us else None,
                assist_name=None if is_us else ev.assist,
            )
        )
    return events


def _sync_match(session: Session, slug: str, content: MatchContent, result: IngestResult) -> None:
    match = session.scalars(select(Match).where(Match.slug == slug)).one_or_none()
    if match is None:
        missing = [
            f
            for f in ("tournament", "kickoff", "home", "opponent", "status")
            if getattr(content, f) is None
        ]
        if missing:
            result.warnings.append(f"matches/{slug}.yaml: new match needs {', '.join(missing)}")
            return
        tournament = session.scalars(
            select(Tournament).where(Tournament.slug == content.tournament)
        ).one_or_none()
        if tournament is None:
            result.warnings.append(f"matches/{slug}.yaml: unknown tournament {content.tournament}")
            return
        match = Match(
            slug=slug, source="manual", tournament_id=tournament.id, season_id=tournament.season_id
        )
        session.add(match)
    if match.source == "manual":
        match.round = content.round
        match.kickoff = content.kickoff
        match.home = bool(content.home)
        match.venue_name = content.venue.name if content.venue else None
        match.venue_address = content.venue.address if content.venue else None
        match.opponent_name = content.opponent.name if content.opponent else ""
        match.opponent_logo = content.opponent.logo if content.opponent else None
        match.status = content.status or "scheduled"
        match.score_us = content.score.us if content.score else None
        match.score_them = content.score.them if content.score else None
    session.flush()
    if content.events and (match.source == "manual" or not match.events):
        match.events.clear()
        session.flush()
        match.events.extend(_events(session, content))
    if content.mvp:
        match.mvp_player_id = _player_id_by_slug(session, content.mvp)
    match.report_news_slug = content.report_news or match.report_news_slug
    match.stream_url = content.stream_url or match.stream_url
    match.video_url = content.video_url or match.video_url
    if content.squad:
        session.execute(delete(MatchAppearance).where(MatchAppearance.match_id == match.id))
        for player_slug in content.squad:
            player_id = _player_id_by_slug(session, player_slug)
            if player_id is None:
                result.warnings.append(f"matches/{slug}.yaml: unknown player {player_slug}")
                continue
            session.add(MatchAppearance(match_id=match.id, player_id=player_id))
    session.flush()
    result.tags.add(f"match:{slug}")


def sync_content(session: Session, bundle: ContentBundle) -> IngestResult:
    result = IngestResult()
    _set_doc(session, "club", bundle.club)
    _set_doc(session, "history", bundle.history)

    for t in bundle.tournaments:
        season = ensure_season(session, t.season)
        tournament = session.scalars(
            select(Tournament).where(Tournament.slug == t.slug)
        ).one_or_none()
        if tournament is None:
            tournament = Tournament(slug=t.slug, source="manual")
            session.add(tournament)
        tournament.name, tournament.short, tournament.kind = t.name, t.short, t.kind
        tournament.url, tournament.season_id = t.url, season.id
    session.flush()

    for slug, content in bundle.players.items():
        player = _sync_player(session, slug, content)
        result.tags.add(f"player:{player.slug}")

    keep = {n.slug for n in bundle.news}
    session.execute(delete(News).where(News.slug.not_in(keep)))
    for n in bundle.news:
        news = session.scalars(select(News).where(News.slug == n.slug)).one_or_none()
        if news is None:
            news = News(slug=n.slug)
            session.add(news)
        news.date, news.tag, news.title, news.lead = n.date, n.tag, n.title, n.lead
        news.body_md, news.cover, news.featured = n.body, n.cover, n.featured
        news.match_slug = n.match
        news.source_platform = n.source.platform if n.source else None
        news.source_url = n.source.url if n.source else None
        result.tags.add(f"news:{n.slug}")
    session.flush()

    for slug, content in bundle.matches.items():
        _sync_match(session, slug, content, result)

    result.counts = {
        "players": len(bundle.players),
        "news": len(bundle.news),
        "matches": len(bundle.matches),
    }
    result.tags |= {"club", "history", "news", "players", "matches", "home", "stats"}
    return result
```

- [ ] **Step 3: Тесты зелёные**

Run: `uv run pytest worker/tests/test_pipeline_content.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add worker && git commit -m "feat(worker): sync content/ into database with manual overrides"
```

---

### Task 7: Статистика и пересчёт агрегатов

**Files:**
- Create: `core/bu_core/stats.py`, `core/bu_core/recompute.py`
- Test: `core/tests/test_stats.py`, `core/tests/test_recompute.py`

**Interfaces:**
- Produces (`stats`, чистые функции):
  - `Result(slug: str, kickoff: datetime, us: int, them: int)`; `outcome(us, them) -> "W"|"D"|"L"`
  - `form(results: list[Result], n=5) -> list[dict]` — элементы `{"slug","outcome","us","them"}`, от старого к новому
  - `totals(results) -> dict` — `played, won, drawn, lost, gf, ga, clean_sheets`
  - `StatLine(player_id: int, slug: str, name: str, played, goals, assists, yellow, red, mvp)`
  - `leaders(lines: list[StatLine], key: str, n=5) -> list[dict]` — сортировка: значение ↓, матчи ↑, имя; нулевые значения исключаются; элемент `{"slug","name","value","played"}`
  - `records(results, goal_minutes: list[tuple[str, int]], appearances: dict[str, int]) -> dict` — ключи `biggest_win`, `unbeaten_streak`, `fastest_goal`, `most_appearances` (каждый `None` при отсутствии данных)
- Produces (`recompute`): `recompute(session) -> None` — заполняет `PlayerSeasonStats` и `Computed` с ключами `meta` (`{"current_season": slug|None}`), `season:<slug>` (`{"form","totals","leaders":{"goals","assists","mvp"}}`), `club` (`{"records","numbers":{"founded","matches","goals","trophies"}}`).

Источник статистики игрока: для турниров с `source != "manual"` — `PlayerTournamentStats`; для `manual` — `MatchAppearance` (матчи) и `MatchEvent` (голы/ассисты/карточки). MVP — `Match.mvp_player_id` по всем турнирам.

- [ ] **Step 1: Падающие тесты чистых функций**

`core/tests/test_stats.py`:
```python
from datetime import UTC, datetime, timedelta

from bu_core.stats import Result, StatLine, form, leaders, outcome, records, totals

T0 = datetime(2026, 9, 1, tzinfo=UTC)


def r(i: int, us: int, them: int) -> Result:
    return Result(slug=f"m{i}", kickoff=T0 + timedelta(days=i), us=us, them=them)


def test_outcome():
    assert [outcome(2, 1), outcome(1, 1), outcome(0, 3)] == ["W", "D", "L"]


def test_form_last_five_oldest_first():
    results = [r(i, i % 3, 1) for i in range(7)]
    f = form(list(reversed(results)))
    assert [x["slug"] for x in f] == ["m2", "m3", "m4", "m5", "m6"]


def test_totals():
    t = totals([r(0, 2, 0), r(1, 1, 1), r(2, 0, 3)])
    assert t == {"played": 3, "won": 1, "drawn": 1, "lost": 1, "gf": 3, "ga": 4, "clean_sheets": 1}


def test_leaders_tiebreak_and_zero_filter():
    lines = [
        StatLine(1, "a", "Анна", played=5, goals=3, assists=0, yellow=0, red=0, mvp=0),
        StatLine(2, "b", "Борис", played=3, goals=3, assists=1, yellow=0, red=0, mvp=0),
        StatLine(3, "c", "Вера", played=4, goals=0, assists=0, yellow=0, red=0, mvp=0),
    ]
    top = leaders(lines, "goals")
    assert [x["slug"] for x in top] == ["b", "a"]
    assert top[0] == {"slug": "b", "name": "Борис", "value": 3, "played": 3}


def test_records():
    results = [r(0, 5, 1), r(1, 6, 2), r(2, 1, 1), r(3, 0, 1), r(4, 2, 0)]
    rec = records(
        results, goal_minutes=[("m1", 7), ("m0", 3)], appearances={"Анна": 10, "Борис": 12}
    )
    assert rec["biggest_win"] == {"slug": "m1", "us": 6, "them": 2}
    assert rec["unbeaten_streak"] == {"length": 3, "from": "m0", "to": "m2"}
    assert rec["fastest_goal"] == {"slug": "m0", "minute": 3}
    assert rec["most_appearances"] == {"name": "Борис", "value": 12}
    assert records([], [], {}) == {
        "biggest_win": None,
        "unbeaten_streak": None,
        "fastest_goal": None,
        "most_appearances": None,
    }
```

Run: `uv run pytest core/tests/test_stats.py`
Expected: FAIL.

- [ ] **Step 2: Реализация `stats.py`**

`core/bu_core/stats.py`:
```python
"""Чистые функции командной и игровой статистики (см. 03-data-model.md пакета)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

Outcome = Literal["W", "D", "L"]


@dataclass(frozen=True)
class Result:
    slug: str
    kickoff: datetime
    us: int
    them: int


@dataclass(frozen=True)
class StatLine:
    player_id: int
    slug: str
    name: str
    played: int
    goals: int
    assists: int
    yellow: int
    red: int
    mvp: int


def outcome(us: int, them: int) -> Outcome:
    if us > them:
        return "W"
    return "D" if us == them else "L"


def _chrono(results: list[Result]) -> list[Result]:
    return sorted(results, key=lambda x: x.kickoff)


def form(results: list[Result], n: int = 5) -> list[dict[str, Any]]:
    return [
        {"slug": x.slug, "outcome": outcome(x.us, x.them), "us": x.us, "them": x.them}
        for x in _chrono(results)[-n:]
    ]


def totals(results: list[Result]) -> dict[str, int]:
    outcomes = [outcome(x.us, x.them) for x in results]
    return {
        "played": len(results),
        "won": outcomes.count("W"),
        "drawn": outcomes.count("D"),
        "lost": outcomes.count("L"),
        "gf": sum(x.us for x in results),
        "ga": sum(x.them for x in results),
        "clean_sheets": sum(1 for x in results if x.them == 0),
    }


def leaders(lines: list[StatLine], key: str, n: int = 5) -> list[dict[str, Any]]:
    ranked = sorted(
        (line for line in lines if getattr(line, key) > 0),
        key=lambda line: (-getattr(line, key), line.played, line.name),
    )
    return [
        {"slug": line.slug, "name": line.name, "value": getattr(line, key), "played": line.played}
        for line in ranked[:n]
    ]


def records(
    results: list[Result],
    goal_minutes: list[tuple[str, int]],
    appearances: dict[str, int],
) -> dict[str, Any]:
    chrono = _chrono(results)
    wins = [x for x in chrono if x.us > x.them]
    biggest = max(wins, key=lambda x: (x.us - x.them, x.us), default=None)

    best: tuple[int, str, str] | None = None
    run: list[Result] = []
    for x in chrono:
        if x.us >= x.them:
            run.append(x)
            if best is None or len(run) > best[0]:
                best = (len(run), run[0].slug, run[-1].slug)
        else:
            run = []

    fastest = min(goal_minutes, key=lambda g: g[1], default=None)
    most = max(appearances.items(), key=lambda kv: kv[1], default=None)
    return {
        "biggest_win": {"slug": biggest.slug, "us": biggest.us, "them": biggest.them}
        if biggest
        else None,
        "unbeaten_streak": {"length": best[0], "from": best[1], "to": best[2]} if best else None,
        "fastest_goal": {"slug": fastest[0], "minute": fastest[1]} if fastest else None,
        "most_appearances": {"name": most[0], "value": most[1]} if most else None,
    }
```

Run: `uv run pytest core/tests/test_stats.py` → PASS.

- [ ] **Step 3: Падающий тест пересчёта**

`core/tests/test_recompute.py`:
```python
from datetime import UTC, datetime

from bu_core.models import (
    Computed,
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    Player,
    PlayerSeasonStats,
    PlayerTournamentStats,
    Season,
    Tournament,
)
from bu_core.recompute import recompute


def test_recompute_mixes_sources(db):
    season = Season(slug="2026-27", label="2026/27")
    jf = Tournament(
        slug="li",
        name="Лига Инженеров",
        short="ЛИ",
        source="joinfootball",
        external_id="1",
        season=season,
    )
    manual = Tournament(slug="lfl", name="ЛФЛ", short="ЛФЛ", source="manual", season=season)
    p = Player(
        slug="a-k", first_name="А", last_name="К", aliases=[], manual_fields=[], achievements=[]
    )
    db.add_all([season, jf, manual, p])
    db.flush()
    db.add(
        PlayerTournamentStats(
            player_id=p.id, tournament_id=jf.id, played=5, goals=2, assists=6, yellow=1, red=0
        )
    )
    m1 = Match(
        slug="m1",
        tournament_id=jf.id,
        season_id=season.id,
        home=True,
        kickoff=datetime(2026, 9, 6, tzinfo=UTC),
        opponent_name="X",
        status="finished",
        score_us=2,
        score_them=0,
        source="joinfootball",
        external_id="1",
        mvp_player_id=p.id,
    )
    m2 = Match(
        slug="m2",
        tournament_id=manual.id,
        season_id=season.id,
        home=False,
        kickoff=datetime(2026, 10, 11, tzinfo=UTC),
        opponent_name="Y",
        status="finished",
        score_us=1,
        score_them=1,
        source="manual",
    )
    m2.events.append(MatchEvent(minute=4, type="goal", team="us", player_id=p.id))
    db.add_all([m1, m2])
    db.flush()
    m1.events.append(MatchEvent(minute=9, type="goal", team="us", player_id=p.id))
    db.add(MatchAppearance(match_id=m2.id, player_id=p.id))
    db.add(ContentDoc(key="club", data={"founded": 2019}))
    db.add(ContentDoc(key="history", data={"trophies": [{"place": 1}, {"place": 2}]}))
    db.flush()

    recompute(db)

    line = db.get(PlayerSeasonStats, (p.id, season.id))
    assert (line.played, line.goals, line.assists, line.yellow, line.mvp) == (6, 3, 6, 1, 1)
    assert db.get(Computed, "meta").data == {"current_season": "2026-27"}
    season_doc = db.get(Computed, "season:2026-27").data
    assert [f["outcome"] for f in season_doc["form"]] == ["W", "D"]
    assert season_doc["leaders"]["goals"][0]["slug"] == "a-k"
    club = db.get(Computed, "club").data
    assert club["numbers"] == {"founded": 2019, "matches": 2, "goals": 3, "trophies": 1}
    assert club["records"]["fastest_goal"] == {"slug": "m2", "minute": 4}


def test_recompute_empty_db(db):
    recompute(db)
    assert db.get(Computed, "meta").data == {"current_season": None}
```

Run: `uv run pytest core/tests/test_recompute.py` → FAIL.

- [ ] **Step 4: Реализация `recompute.py`**

`core/bu_core/recompute.py`:
```python
"""Пересчёт агрегатов, которые API только читает."""

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bu_core.models import (
    Computed,
    ContentDoc,
    Match,
    MatchAppearance,
    MatchEvent,
    Player,
    PlayerSeasonStats,
    PlayerTournamentStats,
    Season,
    Tournament,
)
from bu_core.stats import Result, StatLine, form, leaders, records, totals

FIELDS = ("played", "goals", "assists", "yellow", "red", "mvp")


def _put(session: Session, key: str, data: dict[str, Any]) -> None:
    row = session.get(Computed, key)
    if row is None:
        session.add(Computed(key=key, data=data))
    else:
        row.data = data


def _season_lines(session: Session) -> dict[tuple[int, int], dict[str, int]]:
    lines: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: dict.fromkeys(FIELDS, 0))

    rows = session.execute(
        select(PlayerTournamentStats, Tournament.season_id)
        .join(Tournament, Tournament.id == PlayerTournamentStats.tournament_id)
        .where(Tournament.source != "manual")
    )
    for stats, season_id in rows:
        line = lines[(stats.player_id, season_id)]
        for f in ("played", "goals", "assists", "yellow", "red"):
            line[f] += getattr(stats, f)

    manual = select(Match.id).join(Tournament).where(Tournament.source == "manual")
    for player_id, season_id in session.execute(
        select(MatchAppearance.player_id, Match.season_id)
        .join(Match, Match.id == MatchAppearance.match_id)
        .where(Match.id.in_(manual))
    ):
        lines[(player_id, season_id)]["played"] += 1
    for ev, season_id in session.execute(
        select(MatchEvent, Match.season_id)
        .join(Match, Match.id == MatchEvent.match_id)
        .where(Match.id.in_(manual), MatchEvent.team == "us")
    ):
        if ev.player_id and ev.type in ("goal", "penalty"):
            lines[(ev.player_id, season_id)]["goals"] += 1
        if ev.assist_id and ev.type in ("goal", "penalty"):
            lines[(ev.assist_id, season_id)]["assists"] += 1
        if ev.player_id and ev.type in ("yellow", "red"):
            lines[(ev.player_id, season_id)][ev.type] += 1

    for player_id, season_id in session.execute(
        select(Match.mvp_player_id, Match.season_id).where(Match.mvp_player_id.is_not(None))
    ):
        lines[(player_id, season_id)]["mvp"] += 1
    return lines


def recompute(session: Session) -> None:
    lines = _season_lines(session)
    session.execute(delete(PlayerSeasonStats))
    for (player_id, season_id), values in lines.items():
        session.add(PlayerSeasonStats(player_id=player_id, season_id=season_id, **values))
    session.flush()

    players = {p.id: p for p in session.scalars(select(Player))}
    seasons = {s.id: s for s in session.scalars(select(Season))}
    finished = session.scalars(select(Match).where(Match.status == "finished")).all()
    all_matches = session.scalars(select(Match).order_by(Match.kickoff)).all()

    now = datetime.now(UTC)
    current = None
    past_or_soon = [m for m in all_matches if m.kickoff <= now] or all_matches
    if past_or_soon:
        current = seasons[past_or_soon[-1].season_id].slug
    _put(session, "meta", {"current_season": current})

    for season in seasons.values():
        results = [
            Result(m.slug, m.kickoff, m.score_us or 0, m.score_them or 0)
            for m in finished
            if m.season_id == season.id
        ]
        stat_lines = [
            StatLine(
                pid,
                players[pid].slug,
                f"{players[pid].first_name} {players[pid].last_name}".strip(),
                **values,
            )
            for (pid, sid), values in lines.items()
            if sid == season.id
        ]
        _put(
            session,
            f"season:{season.slug}",
            {
                "form": form(results),
                "totals": totals(results),
                "leaders": {k: leaders(stat_lines, k) for k in ("goals", "assists", "mvp")},
            },
        )

    all_results = [Result(m.slug, m.kickoff, m.score_us or 0, m.score_them or 0) for m in finished]
    goal_minutes = [
        (slug, minute)
        for slug, minute in session.execute(
            select(Match.slug, MatchEvent.minute)
            .join(Match, Match.id == MatchEvent.match_id)
            .where(MatchEvent.team == "us", MatchEvent.type.in_(("goal", "penalty")))
        )
    ]
    appearances: dict[str, int] = defaultdict(int)
    for (pid, _sid), values in lines.items():
        p = players[pid]
        appearances[f"{p.first_name} {p.last_name}".strip()] += values["played"]

    club = session.get(ContentDoc, "club")
    history = session.get(ContentDoc, "history")
    trophies = (history.data.get("trophies") if history else None) or []
    _put(
        session,
        "club",
        {
            "records": records(all_results, goal_minutes, dict(appearances)),
            "numbers": {
                "founded": club.data.get("founded") if club else None,
                "matches": len(finished),
                "goals": sum(m.score_us or 0 for m in finished),
                "trophies": sum(1 for t in trophies if t.get("place") == 1),
            },
        },
    )
    session.flush()
```

- [ ] **Step 5: Тесты зелёные**

Run: `uv run pytest core/tests -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core && git commit -m "feat(core): stats functions and aggregate recompute"
```

---

### Task 8: HTTP-клиент, снапшоты, уведомления, CLI и планировщик

**Files:**
- Create: `worker/bu_worker/http.py`, `worker/bu_worker/snapshots.py`, `worker/bu_worker/notify.py`, `worker/bu_worker/sources/joinfootball/fetch.py`, `worker/bu_worker/runner.py`, `worker/bu_worker/__main__.py`, `worker/bu_worker/schedule.py`
- Test: `worker/tests/test_http.py`, `worker/tests/test_runner.py`

**Interfaces:**
- Consumes: всё из Tasks 3–7; `get_settings()`.
- Produces:
  - `http.PoliteClient(base_url, user_agent, delay_s, transport=None)` с `.get(path) -> str` (проверяет robots.txt, пауза, 3 ретрая), исключение `http.DisallowedError`.
  - `snapshots.save(root: Path, source: str, name: str, html: str, now: datetime) -> Path`; `snapshots.prune(root, keep_days, now) -> int`.
  - `notify.Notifier(token, chat_id, transport=None).send(text, key)` — шлёт в Telegram, не чаще раза в 6 ч на `key`; без токена — только лог.
  - `fetch.fetch_bundle(client, tournament_id, team_id, base_url, snapshot) -> JoinFootballBundle`, где `snapshot: Callable[[str, str], None]`.
  - `runner.run_joinfootball(session, settings, client, notifier) -> str` (статус `ok|rejected|error`); `runner.run_content(session, settings) -> str`; `runner.revalidate(settings, tags, transport=None) -> None`.
  - CLI: `uv run python -m bu_worker run joinfootball|content|all`, `uv run python -m bu_worker schedule`.

- [ ] **Step 1: Падающие тесты HTTP-клиента**

`worker/tests/test_http.py`:
```python
import httpx
import pytest

from bu_worker.http import DisallowedError, PoliteClient

ROBOTS = "User-agent: *\nDisallow: /matches\nDisallow: /player\n"


def make(handler):
    return PoliteClient(
        "https://jf.test", "BaumanUnitedBot/1.0", delay_s=0, transport=httpx.MockTransport(handler)
    )


def test_respects_robots_and_sets_user_agent():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.headers["user-agent"]))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        return httpx.Response(200, text="<html>ok</html>")

    client = make(handler)
    assert client.get("/match/1") == "<html>ok</html>"
    with pytest.raises(DisallowedError):
        client.get("/player/5")
    assert ("/match/1", "BaumanUnitedBot/1.0") in seen
    assert all(path != "/player/5" for path, _ in seen)


def test_retries_server_errors():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(502) if calls["n"] < 3 else httpx.Response(200, text="ok")

    assert make(handler).get("/tournament/1") == "ok"
    assert calls["n"] == 3
```

Run: `uv run pytest worker/tests/test_http.py` → FAIL.

- [ ] **Step 2: Реализация клиента, снапшотов, уведомлений**

`worker/bu_worker/http.py`:
```python
import time
import urllib.robotparser

import httpx


class DisallowedError(Exception):
    pass


class PoliteClient:
    """HTTP-клиент, который уважает robots.txt и не торопится."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        delay_s: float,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": user_agent},
            timeout=20.0,
            follow_redirects=True,
            transport=transport,
        )
        self._agent = user_agent.split("/")[0]
        self._delay = delay_s
        self._last = 0.0
        self._robots: urllib.robotparser.RobotFileParser | None = None

    def _wait(self) -> None:
        pause = self._delay - (time.monotonic() - self._last)
        if pause > 0:
            time.sleep(pause)
        self._last = time.monotonic()

    def _allowed(self, path: str) -> bool:
        if self._robots is None:
            self._robots = urllib.robotparser.RobotFileParser()
            self._wait()
            response = self._client.get("/robots.txt")
            lines = response.text.splitlines() if response.status_code == 200 else []
            self._robots.parse(lines)
        return self._robots.can_fetch(self._agent, path)

    def get(self, path: str) -> str:
        if not self._allowed(path):
            raise DisallowedError(path)
        last_error: Exception | None = None
        for attempt in range(3):
            self._wait()
            try:
                response = self._client.get(path)
                if response.status_code < 500:
                    response.raise_for_status()
                    return response.text
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )
            except httpx.TransportError as exc:
                last_error = exc
            time.sleep(min(2**attempt, 8) if self._delay else 0)
        assert last_error is not None
        raise last_error
```

`worker/bu_worker/snapshots.py`:
```python
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def save(root: Path, source: str, name: str, html: str, now: datetime) -> Path:
    folder = root / source / now.strftime("%Y-%m-%d-%H%M")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    return path


def prune(root: Path, keep_days: int, now: datetime) -> int:
    cutoff = (now - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    removed = 0
    for folder in root.glob("*/*"):
        if folder.is_dir() and folder.name[:10] < cutoff:
            shutil.rmtree(folder)
            removed += 1
    return removed
```

`worker/bu_worker/notify.py`:
```python
import logging
import time

import httpx

log = logging.getLogger(__name__)
COOLDOWN_S = 6 * 3600


class Notifier:
    def __init__(
        self, token: str | None, chat_id: str | None, transport: httpx.BaseTransport | None = None
    ):
        self._token, self._chat_id = token, chat_id
        self._transport = transport
        self._sent: dict[str, float] = {}

    def send(self, text: str, key: str) -> None:
        log.warning("alert [%s]: %s", key, text)
        if not self._token or not self._chat_id:
            return
        now = time.monotonic()
        if now - self._sent.get(key, -COOLDOWN_S) < COOLDOWN_S:
            return
        self._sent[key] = now
        try:
            with httpx.Client(transport=self._transport, timeout=10) as client:
                client.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage",
                    json={"chat_id": self._chat_id, "text": f"⚠️ bu-site: {text}"},
                )
        except httpx.HTTPError:
            log.exception("telegram alert failed")
```

- [ ] **Step 3: Сбор бандла по сети**

`worker/bu_worker/sources/joinfootball/fetch.py`:
```python
from collections.abc import Callable

from bu_worker.dto import JoinFootballBundle, MatchDetail
from bu_worker.http import PoliteClient
from bu_worker.sources.joinfootball.parse import (
    parse_application,
    parse_calendar,
    parse_match,
    parse_standings,
    parse_tournament_info,
)


def fetch_bundle(
    client: PoliteClient,
    tournament_id: str,
    team_id: str,
    base_url: str,
    snapshot: Callable[[str, str], None],
) -> JoinFootballBundle:
    def get(name: str, path: str) -> str:
        html = client.get(path)
        snapshot(name, html)
        return html

    calendar_html = get("calendar", f"/tournament/{tournament_id}/calendar")
    info = parse_tournament_info(
        calendar_html, tournament_id, f"{base_url}/tournament/{tournament_id}"
    )
    calendar = [
        e
        for e in parse_calendar(calendar_html, info.period_start, info.period_end)
        if team_id in (e.home_team_id, e.away_team_id)
    ]
    players = parse_application(
        get("application", f"/tournament/{tournament_id}/teams/application?team_id={team_id}")
    )
    standings = parse_standings(get("tables", f"/tournament/{tournament_id}/tables"))
    details: dict[str, MatchDetail] = {}
    for entry in calendar:
        if entry.home_score is not None:
            details[entry.external_id] = parse_match(
                get(f"match_{entry.external_id}", f"/match/{entry.external_id}")
            )
    return JoinFootballBundle(
        tournament=info, players=players, calendar=calendar, details=details, standings=standings
    )
```

- [ ] **Step 4: Падающий тест раннера**

`worker/tests/test_runner.py`:
```python
from pathlib import Path

import httpx
from sqlalchemy import select

from bu_core.models import Computed, IngestRun, Match
from bu_core.settings import Settings
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import revalidate, run_joinfootball

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
```

Run: `uv run pytest worker/tests/test_runner.py` → FAIL.

- [ ] **Step 5: Раннер, CLI, планировщик**

`worker/bu_worker/runner.py`:
```python
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from bu_core.models import IngestRun
from bu_core.recompute import recompute
from bu_core.settings import Settings
from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.pipeline import content as content_pipeline
from bu_worker.pipeline import joinfootball as jf_pipeline
from bu_worker.sources.content import load_content
from bu_worker.sources.joinfootball.fetch import fetch_bundle

log = logging.getLogger(__name__)


def revalidate(
    settings: Settings, tags: set[str], transport: httpx.BaseTransport | None = None
) -> None:
    if not settings.revalidate_url or not tags:
        return
    try:
        with httpx.Client(transport=transport, timeout=10) as client:
            client.post(
                settings.revalidate_url,
                json={"tags": sorted(tags)},
                headers={"Authorization": f"Bearer {settings.revalidate_secret or ''}"},
            )
    except httpx.HTTPError:
        log.exception("revalidate failed")


def _record(
    session: Session, source: str, started: datetime, status: str, counts: dict, error: str | None
) -> None:
    session.add(
        IngestRun(
            source=source,
            started_at=started,
            finished_at=datetime.now(UTC),
            status=status,
            counts=counts,
            error=error,
        )
    )
    session.commit()


def run_joinfootball(
    session: Session, settings: Settings, client: PoliteClient, notifier: Notifier
) -> str:
    overall = "ok"
    all_tags: set[str] = set()
    for tid in settings.joinfootball_tournament_ids:
        source = f"joinfootball:{tid}"
        started = datetime.now(UTC)
        root = Path(settings.snapshot_dir)

        def snap(name: str, html: str, _tid: str = tid, _started: datetime = started) -> None:
            snapshots.save(root, f"joinfootball/{_tid}", name, html, _started)

        try:
            bundle = fetch_bundle(
                client, tid, settings.joinfootball_team_id, settings.joinfootball_base, snap
            )
            jf_pipeline.sanity_check(session, source, bundle)
            result = jf_pipeline.ingest(
                session, bundle, settings.joinfootball_team_id, settings.our_team_names
            )
            recompute(session)
            session.commit()
        except jf_pipeline.SanityError as exc:
            session.rollback()
            _record(session, source, started, "rejected", {}, str(exc))
            notifier.send(f"{source}: данные отклонены — {exc}", key=f"{source}:rejected")
            overall = "rejected"
            continue
        except Exception as exc:  # noqa: BLE001 — любая ошибка источника не должна ронять воркер
            session.rollback()
            log.exception("joinfootball %s failed", tid)
            _record(session, source, started, "error", {}, repr(exc))
            notifier.send(f"{source}: ошибка — {exc!r}", key=f"{source}:error")
            overall = "error"
            continue
        _record(session, source, started, "ok", result.counts, None)
        for warning in result.warnings:
            notifier.send(warning, key=f"warn:{warning}")
        all_tags |= result.tags
    revalidate(settings, all_tags)
    return overall


def run_content(session: Session, settings: Settings) -> str:
    started = datetime.now(UTC)
    bundle = load_content(Path(settings.content_dir))  # ContentError пробрасывается — деплой падает
    result = content_pipeline.sync_content(session, bundle)
    recompute(session)
    session.commit()
    _record(session, "content", started, "ok", result.counts, None)
    for warning in result.warnings:
        log.warning(warning)
    revalidate(settings, result.tags)
    return "ok"
```

`worker/bu_worker/__main__.py`:
```python
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
```

`worker/bu_worker/schedule.py`:
```python
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from bu_core.db import make_engine, make_sessionmaker
from bu_core.models import Match
from bu_core.settings import Settings
from bu_worker import snapshots
from bu_worker.http import PoliteClient
from bu_worker.notify import Notifier
from bu_worker.runner import run_joinfootball

log = logging.getLogger(__name__)


def start(settings: Settings) -> None:
    sessions = make_sessionmaker(make_engine())
    notifier = Notifier(settings.telegram_bot_token, settings.telegram_chat_id)

    def scrape() -> None:
        client = PoliteClient(
            settings.joinfootball_base,
            f"BaumanUnitedBot/1.0 (+{settings.site_url})",
            settings.request_delay_s,
        )
        with sessions() as session:
            run_joinfootball(session, settings, client, notifier)

    def matchday() -> None:
        now = datetime.now(UTC)
        with sessions() as session:
            live = session.scalars(
                select(Match.id).where(
                    Match.kickoff <= now, Match.kickoff >= now - timedelta(hours=3)
                )
            ).first()
        if live is not None:
            scrape()

    def prune() -> None:
        removed = snapshots.prune(
            Path(settings.snapshot_dir), settings.snapshot_keep_days, datetime.now(UTC)
        )
        log.info("pruned %s snapshot folders", removed)

    scheduler = BlockingScheduler(timezone="Europe/Moscow")
    scheduler.add_job(scrape, "interval", hours=6, next_run_time=datetime.now(UTC))
    scheduler.add_job(matchday, "interval", minutes=30)
    scheduler.add_job(prune, "cron", hour=4)
    scheduler.start()
```

- [ ] **Step 6: Тесты зелёные + ручной прогон**

Run: `uv run pytest worker/tests -v`
Expected: PASS.

Run (живой сайт, один раз, на dev-БД): `uv run python -m bu_worker run all`
Expected: код 0; `psql bu_dev -c "select status, counts from ingest_run"` показывает `ok`.

- [ ] **Step 7: Commit**

```bash
git add worker && git commit -m "feat(worker): polite HTTP client, runner, CLI and scheduler"
```

---

### Task 9: API — справочники, матчи, игроки, новости, таблицы

**Files:**
- Create: `api/bu_api/app.py`, `api/bu_api/deps.py`, `api/bu_api/schemas.py`, `api/bu_api/routes/__init__.py`, `api/bu_api/routes/catalog.py`, `api/bu_api/routes/matches.py`, `api/bu_api/routes/players.py`, `api/bu_api/routes/news.py`
- Create: `api/tests/conftest.py`, `api/tests/seed.py`
- Test: `api/tests/test_catalog.py`, `api/tests/test_matches.py`, `api/tests/test_players.py`, `api/tests/test_news.py`

**Interfaces:**
- Consumes: модели и `recompute` (Tasks 1, 7).
- Produces: `create_app(session_factory: Callable[[], Session]) -> FastAPI`; эндпоинты:
  - `GET /health` → `{"ok": true}`
  - `GET /club` → `ContentDoc("club").data` (404, если нет)
  - `GET /history` → `ContentDoc("history").data` или `{"timeline": [], "trophies": [], "legends": []}`
  - `GET /seasons` → `[{"slug","label","final_place"}]`, новые сверху
  - `GET /tournaments?season=` → `[{"slug","name","short","kind","season","url"}]`
  - `GET /standings?tournament=` → `[{"tournament": {...}, "updated_at", "source_url", "rows": [{"pos","team_name","team_logo","played","won","drawn","lost","gf","ga","pts","is_us"}]}]`; без параметра — все турниры текущего сезона
  - `GET /matches?season=&tournament=&where=home|away&status=` → `[MatchSummary]` по возрастанию `kickoff`
  - `GET /matches/{slug}` → `MatchDetail` (404)
  - `GET /players?active=true` → `[PlayerCard]` (статистика текущего сезона), сортировка по позиции GK→DF→MF→FW, затем номер
  - `GET /players/{slug}` → `PlayerDetail` (404)
  - `GET /news?tag=&page=1&per_page=9` → `{"items": [NewsCard], "total", "page", "per_page"}`, сначала featured? — нет: по дате ↓
  - `GET /news/{slug}` → `NewsDetail` (404)

Схемы (`api/bu_api/schemas.py`) — pydantic-модели ответов; полные поля:
- `TournamentOut(slug, name, short, kind, season: str, url: str | None)`
- `MatchSummary(slug, kickoff: datetime, tournament: TournamentOut, round, home: bool, venue_name, venue_address, opponent_name, opponent_logo, status, score_us, score_them, outcome: "W"|"D"|"L"|None, stream_url, source_url)`
- `EventOut(minute, type, team, player_slug, player_name, assist_slug, assist_name, note)` — для наших событий `player_name` = «Имя Фамилия» из БД
- `MatchDetail(MatchSummary + events: list[EventOut], scorers_us: list[str], scorers_them: list[str], mvp: PlayerRef | None, report: NewsCard | None, video_url, prev_slug, next_slug)`
- `PlayerRef(slug, name, number)`
- `PlayerStats(played, goals, assists, yellow, red, mvp)`
- `PlayerCard(slug, first_name, last_name, number, position, nickname, photo, is_captain, season: PlayerStats)`
- `SeasonRow(season: str, label: str, stats: PlayerStats)`
- `PlayerDetail(PlayerCard + role, foot, faculty, joined, fact, achievements: list[dict], seasons: list[SeasonRow], total: PlayerStats, team_best: list[str], prev_slug, next_slug)` — `team_best` — ключи статистики текущего сезона, где игрок №1 в команде (>0)
- `NewsCard(slug, date, tag, title, lead, cover, source_platform, source_url, match_slug, featured)`; `NewsDetail(NewsCard + body_md)`; `NewsPage(items, total, page, per_page)`

- [ ] **Step 1: Сид тестовых данных и фикстура клиента**

`api/tests/seed.py`:
```python
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

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


def seed(db: Session) -> dict:
    season = Season(slug="2026-27", label="2026/27")
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
```

`api/tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient

from bu_api.app import create_app

from .seed import seed


@pytest.fixture
def client(db):
    seed(db)
    return TestClient(create_app(lambda: db))
```

(`TestClient` требует `httpx` — уже в зависимостях `bu-api`.) Добавить `api/tests/__init__.py` (пустой), чтобы работал относительный импорт `.seed`.

- [ ] **Step 2: Падающие тесты**

`api/tests/test_catalog.py`:
```python
def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_club_and_history(client):
    assert client.get("/club").json()["name"] == "Бауман Юнайтед"
    assert client.get("/history").json() == {"timeline": [], "trophies": [], "legends": []}


def test_seasons_and_tournaments(client):
    assert client.get("/seasons").json() == [
        {"slug": "2026-27", "label": "2026/27", "final_place": None}
    ]
    t = client.get("/tournaments", params={"season": "2026-27"}).json()
    assert t[0]["slug"] == "liga-inzhenerov" and t[0]["season"] == "2026-27"


def test_standings_default_current_season(client):
    data = client.get("/standings").json()
    assert data[0]["tournament"]["slug"] == "liga-inzhenerov"
    assert [r["pos"] for r in data[0]["rows"]] == [1, 6]
    assert data[0]["rows"][1]["is_us"] is True
    assert data[0]["source_url"] == "https://jf/tournament/1066703/tables"
```

`api/tests/test_matches.py`:
```python
def test_list_and_filters(client):
    all_matches = client.get("/matches").json()
    assert [m["slug"] for m in all_matches] == ["2026-09-06-bauman-junior", "2026-10-25-messiya"]
    assert all_matches[0]["outcome"] == "L"
    assert all_matches[1]["outcome"] is None
    away = client.get("/matches", params={"where": "away"}).json()
    assert [m["slug"] for m in away] == ["2026-10-25-messiya"]
    finished = client.get("/matches", params={"status": "finished"}).json()
    assert len(finished) == 1


def test_detail(client):
    m = client.get("/matches/2026-09-06-bauman-junior").json()
    assert m["scorers_us"] == ["Королев 22'"]
    assert m["scorers_them"] == ["Горевой 19'"]
    us_goal = next(e for e in m["events"] if e["team"] == "us")
    assert us_goal["player_slug"] == "aleksandr-korolev"
    assert us_goal["player_name"] == "Александр Королев"
    assert m["report"]["slug"] == "start"
    assert m["prev_slug"] is None and m["next_slug"] == "2026-10-25-messiya"


def test_detail_404(client):
    assert client.get("/matches/nope").status_code == 404
```

`api/tests/test_players.py`:
```python
def test_active_players_ordered_with_season_stats(client):
    players = client.get("/players", params={"active": "true"}).json()
    assert [p["slug"] for p in players] == ["egor-kucha", "aleksandr-korolev"]
    assert players[1]["season"]["goals"] == 2
    assert "birth" not in str(players)


def test_player_detail(client):
    p = client.get("/players/aleksandr-korolev").json()
    assert p["nickname"] == "Король"
    assert p["total"]["assists"] == 6
    assert p["seasons"][0]["season"] == "2026-27"
    assert set(p["team_best"]) >= {"goals", "assists"}
    assert client.get("/players/nobody").status_code == 404
```

`api/tests/test_news.py`:
```python
def test_news_pagination_and_tag(client):
    page = client.get("/news", params={"per_page": 1}).json()
    assert page["total"] == 2 and page["items"][0]["slug"] == "club-news"
    tagged = client.get("/news", params={"tag": "match"}).json()
    assert [n["slug"] for n in tagged["items"]] == ["start"]


def test_news_detail(client):
    assert client.get("/news/start").json()["body_md"] == "Текст"
    assert client.get("/news/missing").status_code == 404
```

Run: `uv run pytest api/tests` → FAIL.

- [ ] **Step 3: Каркас приложения и зависимости**

`api/bu_api/deps.py`:
```python
from collections.abc import Callable, Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    factory: Callable[[], Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        if request.app.state.close_sessions:
            session.close()
```

`api/bu_api/app.py`:
```python
from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy.orm import Session

from bu_api.routes import catalog, matches, news, players


def create_app(session_factory: Callable[[], Session], close_sessions: bool = False) -> FastAPI:
    app = FastAPI(title="Bauman United API", version="1.0.0")
    app.state.session_factory = session_factory
    app.state.close_sessions = close_sessions

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    for module in (catalog, matches, players, news):
        app.include_router(module.router)
    return app


def build() -> FastAPI:
    """Точка входа для uvicorn: `uvicorn bu_api.app:build --factory`."""
    from bu_core.db import make_engine, make_sessionmaker

    return create_app(make_sessionmaker(make_engine()), close_sessions=True)
```

- [ ] **Step 4: Схемы и общие хелперы**

`api/bu_api/schemas.py`:
```python
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class TournamentOut(BaseModel):
    slug: str
    name: str
    short: str
    kind: str
    season: str
    url: str | None


class MatchSummary(BaseModel):
    slug: str
    kickoff: datetime
    tournament: TournamentOut
    round: str | None
    home: bool
    venue_name: str | None
    venue_address: str | None
    opponent_name: str
    opponent_logo: str | None
    status: str
    score_us: int | None
    score_them: int | None
    outcome: Literal["W", "D", "L"] | None
    stream_url: str | None
    source_url: str | None


class EventOut(BaseModel):
    minute: int
    type: str
    team: str
    player_slug: str | None
    player_name: str | None
    assist_slug: str | None
    assist_name: str | None
    note: str | None


class PlayerRef(BaseModel):
    slug: str
    name: str
    number: int | None


class NewsCard(BaseModel):
    slug: str
    date: date
    tag: str
    title: str
    lead: str | None
    cover: str | None
    source_platform: str | None
    source_url: str | None
    match_slug: str | None
    featured: bool


class NewsDetail(NewsCard):
    body_md: str


class NewsPage(BaseModel):
    items: list[NewsCard]
    total: int
    page: int
    per_page: int


class MatchDetail(MatchSummary):
    events: list[EventOut]
    scorers_us: list[str]
    scorers_them: list[str]
    mvp: PlayerRef | None
    report: NewsCard | None
    video_url: str | None
    prev_slug: str | None
    next_slug: str | None


class PlayerStats(BaseModel):
    played: int = 0
    goals: int = 0
    assists: int = 0
    yellow: int = 0
    red: int = 0
    mvp: int = 0


class PlayerCard(BaseModel):
    slug: str
    first_name: str
    last_name: str
    number: int | None
    position: str | None
    nickname: str | None
    photo: str | None
    is_captain: bool
    season: PlayerStats


class SeasonRow(BaseModel):
    season: str
    label: str
    stats: PlayerStats


class PlayerDetail(PlayerCard):
    role: str | None
    foot: str | None
    faculty: str | None
    joined: int | None
    fact: str | None
    achievements: list[dict[str, Any]]
    seasons: list[SeasonRow]
    total: PlayerStats
    team_best: list[str]
    prev_slug: str | None
    next_slug: str | None
```

`api/bu_api/routes/__init__.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_core.models import Computed, Match, News, Player, Tournament
from bu_core.stats import outcome
from bu_api.schemas import MatchSummary, NewsCard, TournamentOut


def current_season(session: Session) -> str | None:
    meta = session.get(Computed, "meta")
    return meta.data.get("current_season") if meta else None


def tournament_out(t: Tournament) -> TournamentOut:
    return TournamentOut(
        slug=t.slug, name=t.name, short=t.short, kind=t.kind, season=t.season.slug, url=t.url
    )


def match_summary(m: Match) -> MatchSummary:
    finished = m.status == "finished" and m.score_us is not None and m.score_them is not None
    return MatchSummary(
        slug=m.slug,
        kickoff=m.kickoff,
        tournament=tournament_out(m.tournament),
        round=m.round,
        home=m.home,
        venue_name=m.venue_name,
        venue_address=m.venue_address,
        opponent_name=m.opponent_name,
        opponent_logo=m.opponent_logo,
        status=m.status,
        score_us=m.score_us,
        score_them=m.score_them,
        outcome=outcome(m.score_us, m.score_them) if finished else None,  # type: ignore[arg-type]
        stream_url=m.stream_url,
        source_url=m.source_url,
    )


def news_card(n: News) -> NewsCard:
    return NewsCard(
        slug=n.slug,
        date=n.date,
        tag=n.tag,
        title=n.title,
        lead=n.lead,
        cover=n.cover,
        source_platform=n.source_platform,
        source_url=n.source_url,
        match_slug=n.match_slug,
        featured=n.featured,
    )


def full_name(p: Player) -> str:
    return f"{p.first_name} {p.last_name}".strip()


def players_by_id(session: Session, ids: set[int]) -> dict[int, Player]:
    if not ids:
        return {}
    return {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(ids)))}
```

- [ ] **Step 5: Роуты**

`api/bu_api/routes/catalog.py`:
```python
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, tournament_out
from bu_api.schemas import TournamentOut
from bu_core.models import ContentDoc, Season, StandingRow, Tournament

router = APIRouter()


class SeasonOut(BaseModel):
    slug: str
    label: str
    final_place: str | None


class StandingRowOut(BaseModel):
    pos: int
    team_name: str
    team_logo: str | None
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    pts: int
    is_us: bool


class StandingsOut(BaseModel):
    tournament: TournamentOut
    updated_at: datetime | None
    source_url: str | None
    rows: list[StandingRowOut]


@router.get("/club")
def club(session: Session = Depends(get_session)) -> dict[str, Any]:
    doc = session.get(ContentDoc, "club")
    if doc is None:
        raise HTTPException(404, "club content not synced")
    return doc.data


@router.get("/history")
def history(session: Session = Depends(get_session)) -> dict[str, Any]:
    doc = session.get(ContentDoc, "history")
    base: dict[str, Any] = {"timeline": [], "trophies": [], "legends": []}
    return {**base, **(doc.data if doc else {})}


@router.get("/seasons")
def seasons(session: Session = Depends(get_session)) -> list[SeasonOut]:
    rows = session.scalars(select(Season).order_by(Season.slug.desc()))
    return [SeasonOut(slug=s.slug, label=s.label, final_place=s.final_place) for s in rows]


def _tournaments(session: Session, season: str | None) -> list[Tournament]:
    query = select(Tournament).join(Season).order_by(Tournament.name)
    if season:
        query = query.where(Season.slug == season)
    return list(session.scalars(query))


@router.get("/tournaments")
def tournaments(
    season: str | None = None, session: Session = Depends(get_session)
) -> list[TournamentOut]:
    return [tournament_out(t) for t in _tournaments(session, season)]


@router.get("/standings")
def standings(
    tournament: str | None = None, session: Session = Depends(get_session)
) -> list[StandingsOut]:
    if tournament:
        selected = list(session.scalars(select(Tournament).where(Tournament.slug == tournament)))
    else:
        selected = _tournaments(session, current_season(session))
    out = []
    for t in selected:
        rows = list(
            session.scalars(
                select(StandingRow)
                .where(StandingRow.tournament_id == t.id)
                .order_by(StandingRow.pos)
            )
        )
        if not rows:
            continue
        out.append(
            StandingsOut(
                tournament=tournament_out(t),
                updated_at=max(r.updated_at for r in rows),
                source_url=f"{t.url}/tables" if t.url else None,
                rows=[StandingRowOut.model_validate(r, from_attributes=True) for r in rows],
            )
        )
    return out
```

`api/bu_api/routes/matches.py`:
```python
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import full_name, match_summary, news_card, players_by_id
from bu_api.schemas import EventOut, MatchDetail, MatchSummary, PlayerRef
from bu_core.models import Match, News, Player, Season, Tournament

router = APIRouter()


def _surname(name: str | None) -> str:
    return (name or "").split()[0] if name else "—"


@router.get("/matches")
def list_matches(
    season: str | None = None,
    tournament: str | None = None,
    where: Literal["home", "away"] | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
) -> list[MatchSummary]:
    query = select(Match).join(Tournament).order_by(Match.kickoff)
    if season:
        query = query.join(Season, Season.id == Match.season_id).where(Season.slug == season)
    if tournament:
        query = query.where(Tournament.slug == tournament)
    if where:
        query = query.where(Match.home.is_(where == "home"))
    if status:
        query = query.where(Match.status == status)
    return [match_summary(m) for m in session.scalars(query)]


@router.get("/matches/{slug}")
def match_detail(slug: str, session: Session = Depends(get_session)) -> MatchDetail:
    m = session.scalars(select(Match).where(Match.slug == slug)).one_or_none()
    if m is None:
        raise HTTPException(404, "match not found")
    ids = {i for e in m.events for i in (e.player_id, e.assist_id) if i}
    if m.mvp_player_id:
        ids.add(m.mvp_player_id)
    people = players_by_id(session, ids)

    def ref(pid: int | None) -> Player | None:
        return people.get(pid) if pid else None

    events = []
    scorers_us: list[str] = []
    scorers_them: list[str] = []
    for e in m.events:
        player, assist = ref(e.player_id), ref(e.assist_id)
        events.append(
            EventOut(
                minute=e.minute,
                type=e.type,
                team=e.team,
                player_slug=player.slug if player else None,
                player_name=full_name(player) if player else e.player_name,
                assist_slug=assist.slug if assist else None,
                assist_name=full_name(assist) if assist else e.assist_name,
                note=e.note,
            )
        )
        if e.type in ("goal", "penalty", "own_goal"):
            scorer = player.last_name if player else _surname(e.player_name)
            label = f"{scorer} {e.minute}'" + (" (аг)" if e.type == "own_goal" else "")
            (scorers_us if e.team == "us" else scorers_them).append(label)

    report = None
    if m.report_news_slug:
        news = session.scalars(select(News).where(News.slug == m.report_news_slug)).one_or_none()
        report = news_card(news) if news else None
    if report is None:
        news = session.scalars(select(News).where(News.match_slug == m.slug)).first()
        report = news_card(news) if news else None

    ordered = list(session.scalars(select(Match.slug).order_by(Match.kickoff)))
    i = ordered.index(m.slug)
    mvp = ref(m.mvp_player_id)
    return MatchDetail(
        **match_summary(m).model_dump(),
        events=events,
        scorers_us=scorers_us,
        scorers_them=scorers_them,
        mvp=PlayerRef(slug=mvp.slug, name=full_name(mvp), number=mvp.number) if mvp else None,
        report=report,
        video_url=m.video_url,
        prev_slug=ordered[i - 1] if i > 0 else None,
        next_slug=ordered[i + 1] if i + 1 < len(ordered) else None,
    )
```

`api/bu_api/routes/players.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season
from bu_api.schemas import PlayerCard, PlayerDetail, PlayerStats, SeasonRow
from bu_core.models import Player, PlayerSeasonStats, Season

router = APIRouter()
POSITION_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}
STAT_KEYS = ("played", "goals", "assists", "yellow", "red", "mvp")


def _stats(row: PlayerSeasonStats | None) -> PlayerStats:
    if row is None:
        return PlayerStats()
    return PlayerStats(**{k: getattr(row, k) for k in STAT_KEYS})


def _season_rows(session: Session, slug: str | None) -> dict[int, PlayerSeasonStats]:
    if not slug:
        return {}
    rows = session.scalars(select(PlayerSeasonStats).join(Season).where(Season.slug == slug))
    return {r.player_id: r for r in rows}


def _sorted(players: list[Player]) -> list[Player]:
    return sorted(
        players,
        key=lambda p: (
            POSITION_ORDER.get(p.position or "", 9),
            p.number if p.number is not None else 999,
            p.last_name,
        ),
    )


def _card(p: Player, stats: PlayerStats) -> dict:
    return dict(
        slug=p.slug,
        first_name=p.first_name,
        last_name=p.last_name,
        number=p.number,
        position=p.position,
        nickname=p.nickname,
        photo=p.photo,
        is_captain=p.is_captain,
        season=stats,
    )


@router.get("/players")
def list_players(
    active: bool | None = None, session: Session = Depends(get_session)
) -> list[PlayerCard]:
    query = select(Player)
    if active is not None:
        query = query.where(Player.active.is_(active))
    season_rows = _season_rows(session, current_season(session))
    return [
        PlayerCard(**_card(p, _stats(season_rows.get(p.id))))
        for p in _sorted(list(session.scalars(query)))
    ]


@router.get("/players/{slug}")
def player_detail(slug: str, session: Session = Depends(get_session)) -> PlayerDetail:
    p = session.scalars(select(Player).where(Player.slug == slug)).one_or_none()
    if p is None:
        raise HTTPException(404, "player not found")
    season_slug = current_season(session)
    team_rows = _season_rows(session, season_slug)
    history = session.execute(
        select(PlayerSeasonStats, Season)
        .join(Season, Season.id == PlayerSeasonStats.season_id)
        .where(PlayerSeasonStats.player_id == p.id)
        .order_by(Season.slug.desc())
    ).all()
    seasons = [SeasonRow(season=s.slug, label=s.label, stats=_stats(row)) for row, s in history]
    total = PlayerStats(**{k: sum(getattr(r.stats, k) for r in seasons) for k in STAT_KEYS})
    mine = team_rows.get(p.id)
    team_best = [
        k
        for k in ("goals", "assists", "mvp", "played")
        if mine is not None
        and getattr(mine, k) > 0
        and getattr(mine, k) == max(getattr(r, k) for r in team_rows.values())
    ]
    roster = [
        x.slug
        for x in _sorted(list(session.scalars(select(Player).where(Player.active.is_(True)))))
    ]
    i = roster.index(p.slug) if p.slug in roster else -1
    return PlayerDetail(
        **_card(p, _stats(mine)),
        role=p.role,
        foot=p.foot,
        faculty=p.faculty,
        joined=p.joined,
        fact=p.fact,
        achievements=p.achievements or [],
        seasons=seasons,
        total=total,
        team_best=team_best,
        prev_slug=roster[i - 1] if i > 0 else None,
        next_slug=roster[i + 1] if 0 <= i < len(roster) - 1 else None,
    )
```

`api/bu_api/routes/news.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import news_card
from bu_api.schemas import NewsDetail, NewsPage
from bu_core.models import News

router = APIRouter()


@router.get("/news")
def list_news(
    tag: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(9, ge=1, le=50),
    session: Session = Depends(get_session),
) -> NewsPage:
    query = select(News)
    if tag:
        query = query.where(News.tag == tag)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.order_by(News.date.desc(), News.slug).offset((page - 1) * per_page).limit(per_page)
    )
    return NewsPage(items=[news_card(n) for n in items], total=total, page=page, per_page=per_page)


@router.get("/news/{slug}")
def news_detail(slug: str, session: Session = Depends(get_session)) -> NewsDetail:
    n = session.scalars(select(News).where(News.slug == slug)).one_or_none()
    if n is None:
        raise HTTPException(404, "news not found")
    return NewsDetail(**news_card(n).model_dump(), body_md=n.body_md)
```

- [ ] **Step 6: Тесты зелёные**

Run: `uv run pytest api/tests -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add api && git commit -m "feat(api): catalog, matches, players and news endpoints"
```

---

### Task 10: API — главная, статистика, sitemap, экспорт OpenAPI

**Files:**
- Create: `api/bu_api/routes/home.py`, `api/bu_api/routes/stats.py`, `api/bu_api/routes/sitemap.py`, `api/bu_api/export_openapi.py`
- Modify: `api/bu_api/app.py` (подключить роутеры)
- Test: `api/tests/test_home.py`, `api/tests/test_stats_sitemap.py`

**Interfaces:**
- Produces:
  - `GET /home` → `{"next_match": MatchSummary|None, "last_match": MatchDetail|None, "form": [...], "totals": {...}, "standings": StandingsOut|None (5 строк вокруг нас), "news": [NewsCard] (4), "leaders": {"goals": dict|None, "assists": dict|None, "player_of_month": dict|None}, "numbers": {...}, "live": MatchSummary|None}`
  - `GET /stats?season=` (`season=all` — за всё время) → `{"season": str, "leaders": {...}, "players": [{"slug","name","position","played","goals","assists","ga","yellow","mvp"}], "records": {...}, "seasons": [{"slug","label","gf","ga","final_place"}]}`
  - `GET /sitemap` → `[{"path": str, "lastmod": str|None}]` — статические разделы + матчи + активные/все игроки + новости
  - `uv run python -m bu_api.export_openapi web/openapi.json` пишет схему для генерации TS-типов в плане 2.

- [ ] **Step 1: Падающие тесты**

`api/tests/test_home.py`:
```python
def test_home_aggregate(client):
    home = client.get("/home").json()
    assert home["next_match"]["slug"] == "2026-10-25-messiya"
    assert home["last_match"]["slug"] == "2026-09-06-bauman-junior"
    assert home["last_match"]["scorers_us"] == ["Королев 22'"]
    assert [f["outcome"] for f in home["form"]] == ["L"]
    assert home["standings"]["rows"][-1]["is_us"] is True
    assert len(home["news"]) == 2
    assert home["leaders"]["goals"]["slug"] == "aleksandr-korolev"
    assert home["leaders"]["assists"]["value"] == 6
    assert home["numbers"]["founded"] == 2019
    assert home["live"] is None
```

`api/tests/test_stats_sitemap.py`:
```python
def test_stats_current_and_all(client):
    s = client.get("/stats").json()
    assert s["season"] == "2026-27"
    assert s["leaders"]["goals"][0]["slug"] == "aleksandr-korolev"
    row = next(p for p in s["players"] if p["slug"] == "aleksandr-korolev")
    assert row["ga"] == 8
    assert s["seasons"] == [
        {"slug": "2026-27", "label": "2026/27", "gf": 2, "ga": 3, "final_place": None}
    ]
    assert client.get("/stats", params={"season": "all"}).json()["season"] == "all"


def test_sitemap(client):
    paths = {item["path"] for item in client.get("/sitemap").json()}
    assert {"/", "/matches", "/team", "/news", "/standings", "/about", "/join"} <= paths
    assert "/matches/2026-09-06-bauman-junior" in paths
    assert "/team/aleksandr-korolev" in paths
    assert "/news/start" in paths
```

Run: `uv run pytest api/tests/test_home.py api/tests/test_stats_sitemap.py` → FAIL.

- [ ] **Step 2: `/home`**

`api/bu_api/routes/home.py`:
```python
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, full_name, match_summary, news_card
from bu_api.routes.catalog import standings
from bu_api.routes.matches import match_detail
from bu_core.models import Computed, ContentDoc, Match, News, Player

router = APIRouter()
LIVE_WINDOW = timedelta(hours=2)


def _around_us(table: Any, size: int = 5) -> Any:
    rows = table.rows
    us = next((i for i, r in enumerate(rows) if r.is_us), 0)
    start = max(0, min(us - size // 2, len(rows) - size))
    table.rows = rows[start : start + size]
    return table


@router.get("/home")
def home(session: Session = Depends(get_session)) -> dict[str, Any]:
    now = datetime.now(UTC)
    upcoming = session.scalars(
        select(Match)
        .where(Match.status.in_(("scheduled", "live")), Match.kickoff >= now - LIVE_WINDOW)
        .order_by(Match.kickoff)
    ).first()
    last = session.scalars(
        select(Match).where(Match.status == "finished").order_by(Match.kickoff.desc())
    ).first()
    live = None
    if (
        upcoming
        and upcoming.stream_url
        and (upcoming.status == "live" or upcoming.kickoff <= now <= upcoming.kickoff + LIVE_WINDOW)
    ):
        live = match_summary(upcoming)

    season = current_season(session)
    season_doc = session.get(Computed, f"season:{season}") if season else None
    season_data = season_doc.data if season_doc else {"form": [], "totals": {}, "leaders": {}}
    club_doc = session.get(ContentDoc, "club")
    club = club_doc.data if club_doc else {}
    computed_club = session.get(Computed, "club")

    tables = standings(tournament=club.get("primary_tournament"), session=session)
    leaders = season_data.get("leaders", {})
    pom = club.get("player_of_month")
    if pom and pom.get("player"):
        p = session.scalars(select(Player).where(Player.slug == pom["player"])).one_or_none()
        pom = {**pom, "slug": p.slug, "name": full_name(p), "photo": p.photo} if p else None

    news = session.scalars(select(News).order_by(News.date.desc(), News.slug).limit(4))
    return {
        "next_match": match_summary(upcoming) if upcoming else None,
        "last_match": match_detail(last.slug, session) if last else None,
        "form": season_data.get("form", []),
        "totals": season_data.get("totals", {}),
        "standings": _around_us(tables[0]) if tables else None,
        "news": [news_card(n) for n in news],
        "leaders": {
            "goals": (leaders.get("goals") or [None])[0],
            "assists": (leaders.get("assists") or [None])[0],
            "player_of_month": pom,
        },
        "numbers": computed_club.data["numbers"] if computed_club else {},
        "live": live,
    }
```

- [ ] **Step 3: `/stats` и `/sitemap`**

`api/bu_api/routes/stats.py`:
```python
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import current_season, full_name
from bu_core.models import Computed, Match, Player, PlayerSeasonStats, Season
from bu_core.stats import StatLine, leaders

router = APIRouter()
KEYS = ("played", "goals", "assists", "yellow", "red", "mvp")


@router.get("/stats")
def stats(season: str | None = None, session: Session = Depends(get_session)) -> dict[str, Any]:
    season = season or current_season(session) or "all"
    query = select(PlayerSeasonStats, Season.slug).join(Season)
    if season != "all":
        query = query.where(Season.slug == season)
    sums: dict[int, dict[str, int]] = defaultdict(lambda: dict.fromkeys(KEYS, 0))
    for row, _slug in session.execute(query):
        for k in KEYS:
            sums[row.player_id][k] += getattr(row, k)
    players = {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(sums)))}
    lines = [
        StatLine(pid, players[pid].slug, full_name(players[pid]), **v) for pid, v in sums.items()
    ]
    table = sorted(
        (
            {
                "slug": players[pid].slug,
                "name": full_name(players[pid]),
                "position": players[pid].position,
                **v,
                "ga": v["goals"] + v["assists"],
            }
            for pid, v in sums.items()
        ),
        key=lambda r: (-r["goals"], -r["assists"], r["name"]),
    )
    seasons_out = []
    for s in session.scalars(select(Season).order_by(Season.slug)):
        finished = session.scalars(
            select(Match).where(Match.season_id == s.id, Match.status == "finished")
        ).all()
        seasons_out.append(
            {
                "slug": s.slug,
                "label": s.label,
                "gf": sum(m.score_us or 0 for m in finished),
                "ga": sum(m.score_them or 0 for m in finished),
                "final_place": s.final_place,
            }
        )
    club = session.get(Computed, "club")
    return {
        "season": season,
        "leaders": {k: leaders(lines, k) for k in ("goals", "assists", "mvp")},
        "players": table,
        "records": club.data["records"] if club else {},
        "seasons": seasons_out,
    }
```

`api/bu_api/routes/sitemap.py`:
```python
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_core.models import Match, News, Player

router = APIRouter()
STATIC = ["/", "/matches", "/standings", "/team", "/news", "/about", "/join"]


@router.get("/sitemap")
def sitemap(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    items: list[dict[str, Any]] = [{"path": p, "lastmod": today} for p in STATIC]
    for m in session.scalars(select(Match)):
        items.append(
            {
                "path": f"/matches/{m.slug}",
                "lastmod": m.updated_at.date().isoformat() if m.updated_at else None,
            }
        )
    for p in session.scalars(select(Player)):
        items.append({"path": f"/team/{p.slug}", "lastmod": None})
    for n in session.scalars(select(News)):
        items.append({"path": f"/news/{n.slug}", "lastmod": n.date.isoformat()})
    return items
```

В `api/bu_api/app.py` расширить импорт и цикл:
```python
from bu_api.routes import catalog, home, matches, news, players, sitemap, stats
...
    for module in (catalog, matches, players, news, home, stats, sitemap):
        app.include_router(module.router)
```

`api/bu_api/export_openapi.py`:
```python
import json
import sys
from pathlib import Path

from bu_api.app import create_app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    schema = create_app(lambda: None).openapi()  # type: ignore[arg-type, return-value]
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Тесты, линт, ручная проверка**

Run: `uv run pytest -v && uv run ruff check . && uv run ruff format --check .`
Expected: всё зелёное (при необходимости `uv run ruff format .` и `ruff check --fix`).

Run: `uv run uvicorn bu_api.app:build --factory --port 8000` и `curl -s localhost:8000/home | head -c 600`
Expected: JSON с реальными данными из dev-БД (после Task 8 Step 6).

Run: `uv run python -m bu_api.export_openapi web/openapi.json`
Expected: файл создан.

- [ ] **Step 5: Commit**

```bash
git add api web/openapi.json && git commit -m "feat(api): home, stats, sitemap endpoints and OpenAPI export"
```
