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
    # последний день турнира по сайту лиги: закончившийся турнир не перекачиваем
    period_end: Mapped[date | None] = mapped_column(Date)
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
    kickoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    manual_fields: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
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
    cover_video: Mapped[str | None] = mapped_column(Text)  # гифка из Telegram (mp4)
    source_platform: Mapped[str | None] = mapped_column(String(16))
    source_url: Mapped[str | None] = mapped_column(String(500))
    match_slug: Mapped[str | None] = mapped_column(String(160))
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[str] = mapped_column(String(16), default="content")  # content | telegram


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
