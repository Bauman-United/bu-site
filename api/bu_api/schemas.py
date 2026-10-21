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
    kickoff: datetime | None  # None — дата ещё не назначена («Дата уточняется»)
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
    cover_video: str | None = None


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
    head_to_head: "HeadToHead | None" = None


class HeadToHead(BaseModel):
    won: int
    drawn: int
    lost: int
    recent: list[MatchSummary]


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


class TournamentStatsRow(BaseModel):
    tournament: TournamentOut
    season: str
    stats: PlayerStats


class PlayerDetail(PlayerCard):
    role: str | None
    foot: str | None
    faculty: str | None
    joined: int | None
    fact: str | None
    achievements: list[dict[str, Any]]
    seasons: list[SeasonRow]
    tournaments: list[TournamentStatsRow]
    total: PlayerStats
    team_best: list[str]
    prev_slug: str | None
    next_slug: str | None


class RecordRow(BaseModel):
    rank: int
    slug: str
    name: str
    photo: str | None
    position: str | None
    value: int
    played: int
    active: bool


class GoalContributionRecord(RecordRow):
    goals: int
    assists: int


class GoalkeeperRecord(BaseModel):
    rank: int
    slug: str
    name: str
    photo: str | None
    played: int
    conceded: int
    efficiency: float
    active: bool


class AllTimeRecords(BaseModel):
    """Рекордсмены клуба за всё время, включая гол+пас и эффективность вратарей."""

    goals: list[RecordRow]
    assists: list[RecordRow]
    played: list[RecordRow]
    goal_contributions: list[GoalContributionRecord]
    goalkeepers: list[GoalkeeperRecord]
