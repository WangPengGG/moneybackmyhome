"""Portfolio-related Pydantic models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    """Type of asset in portfolio."""

    STOCK = "stock"
    ETF = "etf"
    OPTION = "option"
    CASH = "cash"


class PositionBase(BaseModel):
    """Base model for a portfolio position."""

    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    asset_type: AssetType = Field(default=AssetType.STOCK)
    quantity: Decimal = Field(..., description="Number of shares/contracts")
    average_cost: Decimal = Field(..., description="Average cost per share")
    target_price: Decimal | None = Field(default=None, description="User's target price")
    stop_loss: Decimal | None = Field(default=None, description="Stop loss price")
    notes: str | None = Field(default=None, description="User notes about the position")


class PositionCreate(PositionBase):
    """Model for creating a new position."""

    pass


class PositionUpdate(BaseModel):
    """Model for updating an existing position."""

    quantity: Decimal | None = None
    average_cost: Decimal | None = None
    target_price: Decimal | None = None
    stop_loss: Decimal | None = None
    notes: str | None = None


class Position(PositionBase):
    """Full position model with computed fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PositionWithMarketData(Position):
    """Position with current market data."""

    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_percent: Decimal | None = None
    day_change: Decimal | None = None
    day_change_percent: Decimal | None = None


class PortfolioSummary(BaseModel):
    """Summary of the entire portfolio."""

    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    total_pnl_percent: Decimal
    positions_count: int
    cash_balance: Decimal = Decimal("0")
    positions: list[PositionWithMarketData] = []


class Transaction(BaseModel):
    """Model for recording transactions."""

    id: int | None = None
    symbol: str
    transaction_type: str  # "BUY", "SELL", "DIVIDEND"
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    executed_at: datetime
    notes: str | None = None
