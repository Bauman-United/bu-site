from bu_core.models import News
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bu_api.deps import get_session
from bu_api.routes import news_card
from bu_api.schemas import NewsDetail, NewsPage

router = APIRouter()


@router.get("/news")
def list_news(
    tag: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(9, ge=1, le=50),
    session: Session = Depends(get_session),
) -> NewsPage:
    query = select(News)
    if tag:
        query = query.where(News.tag == tag)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.order_by(News.date.desc(), News.slug).offset((page - 1) * per_page).limit(per_page)
    )
    return NewsPage(items=[news_card(n) for n in items], total=total, page=page, per_page=per_page)


@router.get("/news/{slug}")
def news_detail(slug: str, session: Session = Depends(get_session)) -> NewsDetail:
    n = session.scalars(select(News).where(News.slug == slug)).one_or_none()
    if n is None:
        raise HTTPException(404, "news not found")
    return NewsDetail(**news_card(n).model_dump(), body_md=n.body_md)
