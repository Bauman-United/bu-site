"""Загрузка и валидация ручного контента из каталога content/."""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import frontmatter
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


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
    # календарный год начала турнира: `season: 2026` (YAML читает его как число);
    # устаревшее «2026-27» принимается и при синхронизации сводится к 2026 с предупреждением
    season: str
    url: str | None = None

    @field_validator("season", mode="before")
    @classmethod
    def _season_year(cls, value: Any) -> str:
        text = str(value).strip()
        if re.fullmatch(r"\d{4}(-\d{2})?", text) is None:
            raise ValueError("season must be a year like 2026")
        return text


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

    @field_validator("kickoff")
    @classmethod
    def _moscow_by_default(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=ZoneInfo("Europe/Moscow"))
        return value


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
