from datetime import date
from typing import Any

from bu_core.models import Match, News, Player
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_api.deps import get_session

router = APIRouter()
STATIC = [
    "/",
    "/matches",
    "/standings",
    "/team",
    "/hall-of-fame",
    "/news",
    "/about",
    "/join",
    "/partners",
]


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
