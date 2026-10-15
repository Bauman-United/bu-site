import os

import pytest
from bu_core.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost/bu_test")


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            outer.rollback()
