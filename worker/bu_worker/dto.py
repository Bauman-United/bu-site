from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Side = Literal["home", "away"]
# assist — голевая передача без привязки к голу (ЛФЛ публикует их отдельным списком)
EventType = Literal["goal", "penalty", "own_goal", "yellow", "red", "assist"]


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
    mvp: int = 0
    goalkeeper_played: int = 0
    goalkeeper_conceded: int = 0
    active: bool = True
    photo_url: str | None = None


class CalendarEntry(BaseModel):
    external_id: str
    kickoff: datetime | None  # None — дата матча на сайте лиги «Не задано»
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


class ParsedAppearance(BaseModel):
    side: Side
    player_name: str
    position: str | None = None


class MatchDetail(BaseModel):
    events: list[ParsedEvent]
    appearances: list[ParsedAppearance] = []
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
    # матчи взяты из календаря команды (многоэтапный турнир): таблицы может не быть
    multi_stage: bool = False
