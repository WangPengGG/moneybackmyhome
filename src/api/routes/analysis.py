"""Analysis API endpoints."""

import logging

from fastapi import APIRouter, Query

from src.tools.market_data import (
    calculate_returns,
    compare_stocks,
    get_historical_prices,
    get_stock_info,
    get_stock_price,
)
from src.tools.options_data import (
    calculate_option_greeks,
    get_option_expirations,
    get_options_chain,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/quote/{symbol}")
async def get_quote(symbol: str) -> dict:
    """Get current stock quote.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Current price and quote data
    """
    return get_stock_price.invoke(symbol)


@router.get("/info/{symbol}")
async def get_info(symbol: str) -> dict:
    """Get company information and fundamentals.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Company information
    """
    return get_stock_info.invoke(symbol)


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("1mo", description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    interval: str = Query("1d", description="Data interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo"),
) -> dict:
    """Get historical price data.

    Args:
        symbol: Stock ticker symbol
        period: Time period
        interval: Data interval

    Returns:
        Historical price data
    """
    return get_historical_prices.invoke({
        "symbol": symbol,
        "period": period,
        "interval": interval,
    })


@router.get("/returns/{symbol}")
async def get_returns(
    symbol: str,
    period: str = Query("1y", description="Time period: 1mo, 3mo, 6mo, 1y, 2y, 5y"),
) -> dict:
    """Calculate returns and statistics for a stock.

    Args:
        symbol: Stock ticker symbol
        period: Time period

    Returns:
        Return metrics and statistics
    """
    return calculate_returns.invoke({"symbol": symbol, "period": period})


@router.post("/compare")
async def compare_multiple_stocks(
    symbols: list[str],
    period: str = Query("1y", description="Time period for comparison"),
) -> dict:
    """Compare performance of multiple stocks.

    Args:
        symbols: List of stock ticker symbols
        period: Time period

    Returns:
        Comparative metrics
    """
    return compare_stocks.invoke({"symbols": symbols, "period": period})


@router.get("/options/{symbol}")
async def get_options(
    symbol: str,
    expiration: str | None = Query(None, description="Specific expiration date (YYYY-MM-DD)"),
) -> dict:
    """Get options chain for a stock.

    Args:
        symbol: Stock ticker symbol
        expiration: Optional expiration date

    Returns:
        Options chain with calls and puts
    """
    return get_options_chain.invoke({
        "symbol": symbol,
        "expiration_date": expiration,
    })


@router.get("/options/{symbol}/expirations")
async def get_expirations(symbol: str) -> dict:
    """Get available option expiration dates.

    Args:
        symbol: Stock ticker symbol

    Returns:
        List of expiration dates
    """
    return get_option_expirations.invoke(symbol)


@router.get("/options/{symbol}/greeks")
async def get_greeks(
    symbol: str,
    strike: float = Query(..., description="Option strike price"),
    expiration: str = Query(..., description="Expiration date (YYYY-MM-DD)"),
    option_type: str = Query("call", description="Option type: call or put"),
) -> dict:
    """Calculate Greeks for a specific option.

    Args:
        symbol: Stock ticker symbol
        strike: Strike price
        expiration: Expiration date
        option_type: call or put

    Returns:
        Option price and Greeks
    """
    return calculate_option_greeks.invoke({
        "symbol": symbol,
        "strike": strike,
        "expiration_date": expiration,
        "option_type": option_type,
    })
