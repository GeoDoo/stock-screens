import pytest
from httpx import Client, ASGITransport
from app.main import app

@pytest.fixture
def client():
    """Reusable httpx client for testing FastAPI."""
    with Client(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
