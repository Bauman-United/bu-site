from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy.orm import Session

from bu_api.routes import catalog, home, matches, news, players, sitemap, stats


def create_app(session_factory: Callable[[], Session], close_sessions: bool = False) -> FastAPI:
    app = FastAPI(title="Bauman United API", version="1.0.0")
    app.state.session_factory = session_factory
    app.state.close_sessions = close_sessions

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    for module in (catalog, matches, players, news, home, stats, sitemap):
        app.include_router(module.router)
    return app


def build() -> FastAPI:
    """Точка входа для uvicorn: `uvicorn bu_api.app:build --factory`."""
    from bu_core.db import make_engine, make_sessionmaker

    return create_app(make_sessionmaker(make_engine()), close_sessions=True)
