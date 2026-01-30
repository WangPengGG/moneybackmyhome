#!/usr/bin/env python
"""Seed sample portfolio data for testing."""

import asyncio
from decimal import Decimal

from src.db import init_db, get_session
from src.db.models import PositionDB
from src.models.portfolio import AssetType


SAMPLE_POSITIONS = [
    {
        "symbol": "AAPL",
        "asset_type": AssetType.STOCK,
        "quantity": Decimal("100"),
        "average_cost": Decimal("175.50"),
        "target_price": Decimal("220.00"),
        "stop_loss": Decimal("150.00"),
        "notes": "Core holding - long term",
    },
    {
        "symbol": "GOOGL",
        "asset_type": AssetType.STOCK,
        "quantity": Decimal("50"),
        "average_cost": Decimal("140.25"),
        "target_price": Decimal("180.00"),
        "notes": "AI play",
    },
    {
        "symbol": "MSFT",
        "asset_type": AssetType.STOCK,
        "quantity": Decimal("75"),
        "average_cost": Decimal("380.00"),
        "target_price": Decimal("450.00"),
        "stop_loss": Decimal("350.00"),
        "notes": "Cloud + AI leader",
    },
    {
        "symbol": "NVDA",
        "asset_type": AssetType.STOCK,
        "quantity": Decimal("30"),
        "average_cost": Decimal("450.00"),
        "target_price": Decimal("600.00"),
        "notes": "GPU/AI infrastructure",
    },
    {
        "symbol": "SPY",
        "asset_type": AssetType.ETF,
        "quantity": Decimal("200"),
        "average_cost": Decimal("450.00"),
        "notes": "S&P 500 index exposure",
    },
    {
        "symbol": "QQQ",
        "asset_type": AssetType.ETF,
        "quantity": Decimal("50"),
        "average_cost": Decimal("380.00"),
        "notes": "NASDAQ exposure",
    },
]


async def seed_data():
    """Insert sample portfolio data."""
    await init_db()

    async with get_session() as session:
        for pos_data in SAMPLE_POSITIONS:
            position = PositionDB(**pos_data)
            session.add(position)

        await session.commit()

    print(f"Seeded {len(SAMPLE_POSITIONS)} positions successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
