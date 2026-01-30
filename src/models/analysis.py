"""Analysis-related Pydantic models."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    """Current stock quote data."""

    symbol: str
    price: Decimal
    change: Decimal
    change_percent: Decimal
    volume: int
    market_cap: Decimal | None = None
    pe_ratio: Decimal | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None
    timestamp: datetime


class StockInfo(BaseModel):
    """Company fundamental information."""

    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    pe_ratio: Decimal | None = None
    forward_pe: Decimal | None = None
    peg_ratio: Decimal | None = None
    price_to_book: Decimal | None = None
    dividend_yield: Decimal | None = None
    beta: Decimal | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None
    avg_volume: int | None = None
    description: str | None = None


class HistoricalPrice(BaseModel):
    """Historical price data point."""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Decimal | None = None


class OptionContract(BaseModel):
    """Single option contract data."""

    contract_symbol: str
    strike: Decimal
    expiration: date
    option_type: str  # "call" or "put"
    last_price: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: Decimal | None = None


class OptionsChain(BaseModel):
    """Options chain for a stock."""

    symbol: str
    expiration_dates: list[date]
    calls: list[OptionContract] = []
    puts: list[OptionContract] = []


class VolatilityData(BaseModel):
    """Volatility metrics for a stock."""

    symbol: str
    historical_volatility_30d: Decimal | None = None
    historical_volatility_60d: Decimal | None = None
    implied_volatility: Decimal | None = None
    iv_percentile: Decimal | None = None
    hv_iv_divergence: Decimal | None = None


class RiskMetrics(BaseModel):
    """Risk analysis metrics."""

    symbol: str | None = None  # None for portfolio-level
    beta: Decimal | None = None
    sharpe_ratio: Decimal | None = None
    max_drawdown: Decimal | None = None
    var_95: Decimal | None = None  # Value at Risk at 95% confidence
    volatility: Decimal | None = None


class ConcentrationRisk(BaseModel):
    """Portfolio concentration analysis."""

    top_holdings: list[dict] = Field(
        default_factory=list,
        description="List of holdings with their weights"
    )
    sector_allocation: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Allocation by sector"
    )
    largest_position_weight: Decimal | None = None
    herfindahl_index: Decimal | None = None  # Concentration measure


class SentimentData(BaseModel):
    """Sentiment analysis data."""

    symbol: str
    overall_sentiment: str  # "bullish", "bearish", "neutral"
    sentiment_score: Decimal = Field(ge=-1, le=1)
    news_count: int = 0
    social_mentions: int = 0
    source: str = "finnhub"
    timestamp: datetime
