from typing import Any

from bu_core.sitemap import sitemap_entries
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bu_api.deps import get_session

router = APIRouter()


@router.get("/sitemap")
def sitemap(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    return [
        {"path": path, "lastmod": lastmod.isoformat() if lastmod else None}
        for path, lastmod in sitemap_entries(session)
    ]
