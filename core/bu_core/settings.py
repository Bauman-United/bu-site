from datetime import date
from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class JoinsportSource(BaseModel):
    """Лига на платформе joinsport (вёрстка и robots как у Bauman League)."""

    key: str  # Tournament.source / Match.source и префикс IngestRun.source
    title: str
    base: str
    team_id: str  # наша команда в этой лиге
    tournament_ids: list[str] = []  # текущие турниры; прошлые находит `run history`


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="BU_", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/bu_dev"
    site_url: str = "http://localhost:3000"
    our_team_names: list[str] = ["Bauman United", "Бауман Юнайтед"]
    joinfootball_base: str = "https://bauman_league.join.football"
    joinfootball_team_id: str = "1089660"
    joinfootball_tournament_ids: list[str] = ["1066703", "1067299"]  # Лига Инженеров, Кубок
    lfl_base: str = "https://lfl.ru"
    lfl_club_id: str = "14270"
    lfl_tournament_ids: list[str] = ["32573", "33238"]
    ingame_base: str = "https://api.ingame-server.ru"
    ingame_public_base: str = "https://ingame-sports.ru"
    ingame_team_id: str = "1997"
    # Прочие лиги на платформе joinsport (Bauman League — поля joinfootball_* выше).
    # Сейчас команда в них не играет: текущих турниров нет, только история.
    joinsport_leagues: list[JoinsportSource] = [
        JoinsportSource(key="ifl", title="IFL", base="https://ifl-bmstu.ru", team_id="1003070"),
        JoinsportSource(
            key="urban", title="Urban Cup", base="https://urban-cup.ru", team_id="1321682"
        ),
    ]
    history_refresh: bool = False  # перекачать и архивные (закончившиеся) турниры
    tg_base: str = "https://t.me"
    tg_channel: str = "baumanunited"
    tg_since: date = date(2026, 7, 1)
    tg_max_pages: int = 40
    tg_full_rescan: bool = False  # перечитать канал до tg_since (после смены правил отбора)
    request_delay_s: float = 3.0
    content_dir: str = "content"
    snapshot_dir: str = "snapshots"
    snapshot_keep_days: int = 7
    # IndexNow: ключ задаём только на проде с открытой индексацией (сайт отдаёт его в /indexnow.txt)
    indexnow_key: str | None = None
    indexnow_endpoint: str = "https://yandex.com/indexnow"
    media_dir: str = "media"  # свои копии картинок из Telegram; сайт отдаёт их как /media/…
    revalidate_url: str | None = None
    revalidate_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_api_base: str = "https://api.telegram.org"
    join_chat_id: str | None = None  # личка владельца для заявок «Хочу в команду»
    join_dry_run: bool = False  # e2e: логировать заявку вместо отправки

    @property
    def joinsport_sources(self) -> list[JoinsportSource]:
        """Все лиги на joinsport: Bauman League (source «joinfootball») и `joinsport_leagues`."""
        bl = JoinsportSource(
            key="joinfootball",
            title="Bauman League",
            base=self.joinfootball_base,
            team_id=self.joinfootball_team_id,
            tournament_ids=self.joinfootball_tournament_ids,
        )
        return [bl, *self.joinsport_leagues]


@lru_cache
def get_settings() -> Settings:
    return Settings()
