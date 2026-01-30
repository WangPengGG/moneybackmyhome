"""Market data tools using yfinance."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import yfinance as yf
from langchain_core.tools import tool

from src.models.analysis import HistoricalPrice, StockInfo, StockQuote

logger = logging.getLogger(__name__)


def _safe_decimal(value: Any) -> Decimal | None:
    """Safely convert a value to Decimal."""
    if value is None or (isinstance(value, float) and (value != value)):  # NaN check
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int."""
    if value is None or (isinstance(value, float) and (value != value)):
        return None
    try:
        return int(value)
    except Exception:
        return None


@tool
def get_stock_price(symbol: str) -> dict:
    """Get the current stock price and basic quote data for a given symbol.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "GOOGL")

    Returns:
        Dictionary containing current price, change, volume, and other quote data.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            return {"error": f"Could not fetch data for symbol: {symbol}"}

        quote = StockQuote(
            symbol=symbol.upper(),
            price=_safe_decimal(info.get("regularMarketPrice")) or Decimal("0"),
            change=_safe_decimal(info.get("regularMarketChange")) or Decimal("0"),
            change_percent=_safe_decimal(info.get("regularMarketChangePercent")) or Decimal("0"),
            volume=_safe_int(info.get("regularMarketVolume")) or 0,
            market_cap=_safe_decimal(info.get("marketCap")),
            pe_ratio=_safe_decimal(info.get("trailingPE")),
            fifty_two_week_high=_safe_decimal(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_safe_decimal(info.get("fiftyTwoWeekLow")),
            timestamp=datetime.now(),
        )

        return quote.model_dump(mode="json")

    except Exception as e:
        logger.error(f"Error fetching stock price for {symbol}: {e}")
        return {"error": str(e)}


@tool
def get_stock_info(symbol: str) -> dict:
    """Get detailed company information and fundamentals for a given symbol.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "GOOGL")

    Returns:
        Dictionary containing company name, sector, industry, and key fundamentals.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info or "shortName" not in info:
            return {"error": f"Could not fetch info for symbol: {symbol}"}

        stock_info = StockInfo(
            symbol=symbol.upper(),
            name=info.get("shortName", info.get("longName", symbol)),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=_safe_decimal(info.get("marketCap")),
            pe_ratio=_safe_decimal(info.get("trailingPE")),
            forward_pe=_safe_decimal(info.get("forwardPE")),
            peg_ratio=_safe_decimal(info.get("pegRatio")),
            price_to_book=_safe_decimal(info.get("priceToBook")),
            dividend_yield=_safe_decimal(info.get("dividendYield")),
            beta=_safe_decimal(info.get("beta")),
            fifty_two_week_high=_safe_decimal(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_safe_decimal(info.get("fiftyTwoWeekLow")),
            avg_volume=_safe_int(info.get("averageVolume")),
            description=info.get("longBusinessSummary"),
        )

        return stock_info.model_dump(mode="json")

    except Exception as e:
        logger.error(f"Error fetching stock info for {symbol}: {e}")
        return {"error": str(e)}


@tool
def get_historical_prices(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d"
) -> dict:
    """Get historical price data for a given symbol.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "GOOGL")
        period: Time period to fetch. Options: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
        interval: Data interval. Options: "1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"

    Returns:
        Dictionary containing a list of historical price data points.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return {"error": f"No historical data for symbol: {symbol}"}

        prices = []
        for idx, row in hist.iterrows():
            price = HistoricalPrice(
                date=idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10]),
                open=_safe_decimal(row["Open"]) or Decimal("0"),
                high=_safe_decimal(row["High"]) or Decimal("0"),
                low=_safe_decimal(row["Low"]) or Decimal("0"),
                close=_safe_decimal(row["Close"]) or Decimal("0"),
                volume=_safe_int(row["Volume"]) or 0,
                adjusted_close=_safe_decimal(row.get("Adj Close")),
            )
            prices.append(price.model_dump(mode="json"))

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "count": len(prices),
            "prices": prices,
        }

    except Exception as e:
        logger.error(f"Error fetching historical prices for {symbol}: {e}")
        return {"error": str(e)}


@tool
def get_multiple_stock_prices(symbols: list[str]) -> dict:
    """Get current prices for multiple stocks at once.

    Args:
        symbols: List of stock ticker symbols (e.g., ["AAPL", "GOOGL", "MSFT"])

    Returns:
        Dictionary with symbol as key and quote data as value.
    """
    results = {}
    for symbol in symbols:
        results[symbol.upper()] = get_stock_price.invoke(symbol)
    return results


@tool
def calculate_returns(symbol: str, period: str = "1y") -> dict:
    """Calculate returns and basic statistics for a stock.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL")
        period: Time period for calculation. Options: "1mo", "3mo", "6mo", "1y", "2y", "5y"

    Returns:
        Dictionary containing return metrics and statistics.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period)

        if hist.empty or len(hist) < 2:
            return {"error": f"Insufficient data for {symbol}"}

        # Calculate returns
        first_price = float(hist["Close"].iloc[0])
        last_price = float(hist["Close"].iloc[-1])
        total_return = ((last_price - first_price) / first_price) * 100

        # Daily returns for volatility
        daily_returns = hist["Close"].pct_change().dropna()

        # Annualized volatility (assuming 252 trading days)
        volatility = float(daily_returns.std() * (252 ** 0.5) * 100)

        # Max drawdown
        rolling_max = hist["Close"].expanding().max()
        drawdowns = (hist["Close"] - rolling_max) / rolling_max
        max_drawdown = float(drawdowns.min() * 100)

        return {
            "symbol": symbol.upper(),
            "period": period,
            "start_price": round(first_price, 2),
            "end_price": round(last_price, 2),
            "total_return_percent": round(total_return, 2),
            "annualized_volatility_percent": round(volatility, 2),
            "max_drawdown_percent": round(max_drawdown, 2),
            "trading_days": len(hist),
        }

    except Exception as e:
        logger.error(f"Error calculating returns for {symbol}: {e}")
        return {"error": str(e)}


@tool
def compare_stocks(symbols: list[str], period: str = "1y") -> dict:
    """Compare performance of multiple stocks over a period.

    Args:
        symbols: List of stock ticker symbols to compare
        period: Time period for comparison. Options: "1mo", "3mo", "6mo", "1y", "2y"

    Returns:
        Dictionary with comparative metrics for each stock.
    """
    results = {}
    for symbol in symbols:
        returns_data = calculate_returns.invoke({"symbol": symbol, "period": period})
        if "error" not in returns_data:
            results[symbol.upper()] = returns_data

    if not results:
        return {"error": "Could not fetch data for any of the provided symbols"}

    # Sort by total return
    sorted_symbols = sorted(
        results.keys(),
        key=lambda s: results[s].get("total_return_percent", 0),
        reverse=True
    )

    return {
        "period": period,
        "stocks": results,
        "ranking_by_return": sorted_symbols,
    }
