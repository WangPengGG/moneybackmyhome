"""Economic calendar tools using Finnhub API."""

import logging
from datetime import date, datetime, timedelta

import httpx
import yfinance as yf
from langchain_core.tools import tool
from sqlalchemy import select

from src.config import get_settings
from src.db import PositionDB, get_session

logger = logging.getLogger(__name__)

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def _get_finnhub_key() -> str | None:
    """Get Finnhub API key from settings."""
    settings = get_settings()
    key = settings.finnhub_api_key
    return key if key else None


async def _fetch_finnhub(endpoint: str, params: dict | None = None) -> dict | None:
    """Fetch data from Finnhub API.

    Args:
        endpoint: API endpoint (e.g., "/calendar/economic")
        params: Query parameters

    Returns:
        JSON response or None if error
    """
    api_key = _get_finnhub_key()
    if not api_key:
        return None

    params = params or {}
    params["token"] = api_key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FINNHUB_BASE_URL}{endpoint}",
                params=params,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Finnhub API error: {e}")
        return None


@tool
async def get_upcoming_macro_events(days: int = 7) -> dict:
    """Get upcoming economic events that may affect portfolio.

    Retrieves major economic calendar events like FOMC meetings,
    CPI releases, employment reports, and other market-moving data.

    Args:
        days: Number of days to look ahead (default 7, max 30)

    Returns:
        Dictionary containing:
        - events: List of {date, event, country, impact, actual, estimate, previous}
        - event_count: Number of events found

    Note: Requires FINNHUB_API_KEY in .env for full data
    """
    try:
        days = min(max(1, days), 30)  # Clamp to 1-30 days

        today = date.today()
        end_date = today + timedelta(days=days)

        # Try Finnhub API first
        api_key = _get_finnhub_key()

        if api_key:
            data = await _fetch_finnhub(
                "/calendar/economic",
                params={
                    "from": today.isoformat(),
                    "to": end_date.isoformat(),
                }
            )

            if data and "economicCalendar" in data:
                events = []
                for event in data["economicCalendar"]:
                    # Filter for high and medium impact events
                    impact = event.get("impact", "low")
                    if impact in ["high", "medium"]:
                        events.append({
                            "date": event.get("time", "")[:10],
                            "time": event.get("time", "")[11:16] if len(event.get("time", "")) > 10 else "",
                            "event": event.get("event", ""),
                            "country": event.get("country", ""),
                            "impact": impact,
                            "actual": event.get("actual"),
                            "estimate": event.get("estimate"),
                            "previous": event.get("prev"),
                            "unit": event.get("unit", ""),
                        })

                # Sort by date and impact
                events.sort(key=lambda x: (x["date"], 0 if x["impact"] == "high" else 1))

                return {
                    "events": events[:20],  # Limit to 20 events
                    "event_count": len(events),
                    "period": f"{today.isoformat()} to {end_date.isoformat()}",
                    "source": "finnhub",
                }

        # Fallback: Return known major events (approximate schedule)
        return _get_fallback_calendar(today, end_date)

    except Exception as e:
        logger.error(f"Error in get_upcoming_macro_events: {e}")
        return {"error": str(e)}


def _get_fallback_calendar(start_date: date, end_date: date) -> dict:
    """Generate fallback calendar with recurring major events."""
    events = []

    # Common recurring events (approximate)
    current = start_date
    while current <= end_date:
        weekday = current.weekday()

        # Employment report - first Friday of month
        if weekday == 4 and current.day <= 7:
            events.append({
                "date": current.isoformat(),
                "event": "US Employment Report (approximate)",
                "country": "US",
                "impact": "high",
            })

        # CPI - typically mid-month
        if current.day in [10, 11, 12, 13, 14] and weekday in [1, 2, 3]:
            if not any(e["event"].startswith("CPI") for e in events if e["date"] == current.isoformat()):
                events.append({
                    "date": current.isoformat(),
                    "event": "CPI Release (approximate)",
                    "country": "US",
                    "impact": "high",
                })

        current += timedelta(days=1)

    return {
        "events": events,
        "event_count": len(events),
        "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
        "source": "fallback",
        "note": "Set FINNHUB_API_KEY for accurate economic calendar data",
    }


@tool
async def get_earnings_calendar() -> dict:
    """Get earnings dates for portfolio holdings.

    Retrieves upcoming earnings report dates for all stocks in your portfolio.

    Returns:
        Dictionary containing:
        - upcoming: List of {symbol, date, time} where time is "BMO" (before market open) or "AMC" (after market close)
        - days_until_next: Days until next portfolio earnings
        - past_week: Earnings from the past 7 days
    """
    try:
        # Get portfolio symbols
        async with get_session() as session:
            result = await session.execute(select(PositionDB.symbol))
            symbols = [row[0] for row in result.all()]

        if not symbols:
            return {
                "error": "No positions in portfolio",
                "upcoming": [],
                "days_until_next": None,
            }

        today = date.today()
        upcoming = []
        past_week = []
        api_key = _get_finnhub_key()

        for symbol in symbols:
            earnings_date = None
            earnings_time = "unknown"

            # Try Finnhub API first for more accurate data
            if api_key:
                data = await _fetch_finnhub(
                    "/calendar/earnings",
                    params={
                        "symbol": symbol,
                        "from": (today - timedelta(days=7)).isoformat(),
                        "to": (today + timedelta(days=90)).isoformat(),
                    }
                )

                if data and "earningsCalendar" in data:
                    for earning in data["earningsCalendar"]:
                        if earning.get("symbol", "").upper() == symbol.upper():
                            try:
                                earnings_date = datetime.strptime(
                                    earning.get("date", ""),
                                    "%Y-%m-%d"
                                ).date()
                                # Finnhub uses "bmo" or "amc"
                                hour = earning.get("hour", "")
                                earnings_time = hour.upper() if hour in ["bmo", "amc"] else "unknown"
                                break
                            except (ValueError, TypeError):
                                continue

            # Fallback to yfinance
            if not earnings_date:
                try:
                    ticker = yf.Ticker(symbol)
                    calendar = ticker.calendar

                    if calendar is not None and not calendar.empty:
                        # yfinance calendar structure varies
                        if "Earnings Date" in calendar.index:
                            earnings_dates = calendar.loc["Earnings Date"]
                            if hasattr(earnings_dates, "iloc") and len(earnings_dates) > 0:
                                next_earnings = earnings_dates.iloc[0]
                                if hasattr(next_earnings, "date"):
                                    earnings_date = next_earnings.date()
                                elif isinstance(next_earnings, str):
                                    earnings_date = datetime.strptime(
                                        next_earnings[:10], "%Y-%m-%d"
                                    ).date()

                except Exception as e:
                    logger.debug(f"Could not get earnings for {symbol}: {e}")

            if earnings_date:
                entry = {
                    "symbol": symbol,
                    "date": earnings_date.isoformat(),
                    "time": earnings_time,
                    "days_away": (earnings_date - today).days,
                }

                if earnings_date >= today:
                    upcoming.append(entry)
                elif (today - earnings_date).days <= 7:
                    past_week.append(entry)

        # Sort by date
        upcoming.sort(key=lambda x: x["date"])
        past_week.sort(key=lambda x: x["date"], reverse=True)

        # Find days until next earnings
        days_until_next = None
        if upcoming:
            days_until_next = upcoming[0]["days_away"]

        return {
            "upcoming": upcoming,
            "past_week": past_week,
            "days_until_next": days_until_next,
            "portfolio_symbols": symbols,
            "upcoming_count": len(upcoming),
        }

    except Exception as e:
        logger.error(f"Error in get_earnings_calendar: {e}")
        return {"error": str(e)}
