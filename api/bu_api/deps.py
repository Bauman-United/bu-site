from collections.abc import Callable, Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    factory: Callable[[], Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        if request.app.state.close_sessions:
            session.close()
