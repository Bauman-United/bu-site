"""Публичная веб-версия Telegram-канала (t.me/s/<канал>) -> посты. Сеть здесь не используется."""

import html as html_lib
import re
from collections.abc import Callable
from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

if TYPE_CHECKING:
    from bu_worker.http import PoliteClient

_BG_URL = re.compile(r"background-image:url\('([^']+)'\)")
_LINK = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_BOLD = re.compile(r"<(?:b|strong)>(.*?)</(?:b|strong)>", re.S)
_ITALIC = re.compile(r"<(?:i|em)>(.*?)</(?:i|em)>", re.S)
_BR = re.compile(r"<br\s*/?>")
_TAG = re.compile(r"<[^>]+>")


class TgPost(BaseModel):
    id: int
    url: str
    date: datetime
    text: str  # обычный текст
    markdown: str  # текст с ссылками и выделением
    photo: str | None


def _to_markdown(node: Node) -> str:
    raw = node.html or ""
    inner = raw[raw.find(">") + 1 : raw.rfind("<")]  # без обёртки самого div
    inner = _BR.sub("\n", inner)

    def link(m: re.Match[str]) -> str:
        url, label = html_lib.unescape(m.group(1)), _TAG.sub("", m.group(2)).strip()
        return url if not label or label == url else f"[{label}]({url})"

    inner = _LINK.sub(link, inner)
    inner = _BOLD.sub(lambda m: f"**{_TAG.sub('', m.group(1)).strip()}**", inner)
    inner = _ITALIC.sub(lambda m: _TAG.sub("", m.group(1)), inner)
    text = html_lib.unescape(_TAG.sub("", inner))
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def parse_channel_page(html: str, channel: str) -> tuple[list[TgPost], int | None]:
    """Посты страницы (старые сверху) и id для загрузки предыдущей страницы (?before=)."""
    tree = HTMLParser(html)
    posts: list[TgPost] = []
    for message in tree.css(".tgme_widget_message[data-post]"):
        ref = message.attributes.get("data-post") or ""
        if not ref.startswith(f"{channel}/"):
            continue  # репост из другого канала
        time_node = message.css_first("time[datetime]")
        if time_node is None:
            continue
        text_node = message.css_first(".tgme_widget_message_text")
        photo = None
        for wrap in message.css("a.tgme_widget_message_photo_wrap"):
            found = _BG_URL.search(wrap.attributes.get("style") or "")
            if found:
                photo = found.group(1)
                break
        post_id = int(ref.split("/", 1)[1])
        posts.append(
            TgPost(
                id=post_id,
                url=f"https://t.me/{channel}/{post_id}",
                date=datetime.fromisoformat(time_node.attributes.get("datetime") or ""),
                text=text_node.text(separator="\n", strip=True) if text_node else "",
                markdown=_to_markdown(text_node) if text_node else "",
                photo=photo,
            )
        )
    before = min((p.id for p in posts), default=None)
    return posts, before


def fetch_posts(
    client: "PoliteClient",
    channel: str,
    since: date,
    known_max_id: int | None,
    max_pages: int,
    snapshot: Callable[[str, str], object],
) -> list[TgPost]:
    """Листает канал от новых постов к старым до даты `since` или до уже известных постов."""
    posts: dict[int, TgPost] = {}
    path = f"/s/{channel}"
    for page_no in range(max_pages):
        html = client.get(path)
        snapshot(f"page_{page_no}", html)
        page, before = parse_channel_page(html, channel)
        for post in page:
            if post.date.date() >= since:
                posts[post.id] = post
        if not page or before is None:
            break
        if min(p.date.date() for p in page) < since:
            break
        if known_max_id is not None and before <= known_max_id:
            break
        path = f"/s/{channel}?before={before}"
    return sorted(posts.values(), key=lambda p: p.id)
