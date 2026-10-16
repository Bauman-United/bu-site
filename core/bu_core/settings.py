from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    tg_base: str = "https://t.me"
    tg_channel: str = "baumanunited"
    tg_since: date = date(2026, 7, 1)
    tg_max_pages: int = 40
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
