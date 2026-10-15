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
