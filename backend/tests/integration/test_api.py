"""
Integration tests for API endpoints.

TDD: Writing tests first.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialize database before tests."""
    await init_db()
    yield


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Health endpoint should return ok status."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestWatchlistAPI:
    """Test watchlist endpoints."""

    @pytest.mark.asyncio
    async def test_add_to_watchlist(self):
        """Should add a stock to watchlist."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/watchlist",
                json={"symbol": "AAPL", "target_price": 150.0}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_get_watchlist(self):
        """Should return watchlist items."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/watchlist")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

