import pytest
from bu_api.app import create_app
from fastapi.testclient import TestClient

from .seed import seed


@pytest.fixture
def client(db):
    seed(db)
    return TestClient(create_app(lambda: db))
