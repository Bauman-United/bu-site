"""Посты Telegram-канала -> новости сайта (только «настоящие» посты)."""

import re
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from bu_core.models import News
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_worker.pipeline.common import IngestResult
from bu_worker.sources.telegram import TgPost

MSK = ZoneInfo("Europe/Moscow")
MIN_TEXT = 200  # короче — апдейты счёта, ссылки на трансляции и альбомы
TITLE_MAX = 90
LEAD_MAX = 220
_URL = re.compile(r"https?://\S+")
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")
_TRANSFER = re.compile(r"трансфер|переход|подписани|пополнил|в наши ряды", re.I)
# Не новости: составы на игру и анонсы «день матча» (по началу поста).
_NOT_NEWS = re.compile(
    r"^\W*(наш (стартовый )?состав|стартовый состав|день матча|матч ?д[эе]й|match ?day)", re.I
)
_MATCH = re.compile(r"матч|соперник|кубк|кубок|\bтур\b|сч[её]т|игр[уаеы]\b|состав на", re.I)


@dataclass(frozen=True)
class NewsDraft:
    slug: str
    date: date
    tag: str
    title: str
    lead: str | None
    body_md: str
    cover: str | None
    cover_video: str | None
    source_url: str


def _cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:—-")
    return f"{head}…"


def is_excluded(text: str) -> bool:
    return bool(_NOT_NEWS.match(text.strip()))


def to_news(post: TgPost) -> NewsDraft | None:
    plain = " ".join(_URL.sub("", post.text).split())
    if len(plain) < MIN_TEXT or is_excluded(post.text):
        return None
    parts = [p.strip() for p in _SENTENCE_END.split(post.text) if p.strip()]
    title = _cut(parts[0].rstrip("."), TITLE_MAX)
    rest = " ".join(parts[1:])
    tag = (
        "transfer"
        if _TRANSFER.search(post.text)
        else "match"
        if _MATCH.search(post.text)
        else "club"
    )
    return NewsDraft(
        slug=f"tg-{post.id}",
        date=post.date.astimezone(MSK).date(),
        tag=tag,
        title=title,
        lead=_cut(rest, LEAD_MAX) if rest else None,
        body_md=post.markdown or post.text,
        cover=post.photo,
        cover_video=post.video,
        source_url=post.url,
    )


def ingest(session: Session, posts: list[TgPost]) -> IngestResult:
    result = IngestResult()
    kept = 0
    for post in posts:
        draft = to_news(post)
        if draft is None:
            continue
        kept += 1
        news = session.scalars(select(News).where(News.slug == draft.slug)).one_or_none()
        if news is None:
            news = News(slug=draft.slug, origin="telegram", featured=False)
            session.add(news)
        news.date, news.tag, news.title, news.lead = draft.date, draft.tag, draft.title, draft.lead
        news.body_md, news.cover = draft.body_md, draft.cover
        news.cover_video = draft.cover_video
        news.source_platform, news.source_url = "telegram", draft.source_url
        result.tags.add(f"news:{draft.slug}")
    # Правила отбора могли ужесточиться — убираем уже сохранённые посты, которые им не подходят.
    for news in session.scalars(select(News).where(News.origin == "telegram")):
        if is_excluded(news.body_md):
            result.tags.add(f"news:{news.slug}")
            session.delete(news)
    session.flush()
    result.counts = {"posts": len(posts), "news": kept}
    result.tags |= {"news", "home"}
    return result
