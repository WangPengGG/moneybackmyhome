"""Tests for portfolio API endpoints."""

import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.db import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize database before each test."""
    await init_db()


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestPortfolioAPI:
    """Test suite for portfolio API."""

    @pytest.mark.asyncio
    async def test_get_empty_portfolio(self, client):
        """Test getting an empty portfolio."""
        response = await client.get("/api/portfolio/")

        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "positions" in data

    @pytest.mark.asyncio
    async def test_create_position(self, client):
        """Test creating a new position."""
        position_data = {
            "symbol": "TEST",
            "quantity": "100",
            "average_cost": "50.00",
            "asset_type": "stock",
        }

        response = await client.post("/api/portfolio/positions", json=position_data)

        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "TEST"
        assert float(data["quantity"]) == 100

    @pytest.mark.asyncio
    async def test_get_position(self, client):
        """Test getting a specific position."""
        # First create a position
        await client.post(
            "/api/portfolio/positions",
            json={
                "symbol": "GET_TEST",
                "quantity": "50",
                "average_cost": "100.00",
                "asset_type": "stock",
            },
        )

        # Then fetch it
        response = await client.get("/api/portfolio/positions/GET_TEST")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "GET_TEST"

    @pytest.mark.asyncio
    async def test_delete_position(self, client):
        """Test deleting a position."""
        # First create a position
        await client.post(
            "/api/portfolio/positions",
            json={
                "symbol": "DEL_TEST",
                "quantity": "25",
                "average_cost": "75.00",
                "asset_type": "stock",
            },
        )

        # Then delete it
        response = await client.delete("/api/portfolio/positions/DEL_TEST")

        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get("/api/portfolio/positions/DEL_TEST")
        assert response.status_code == 404
