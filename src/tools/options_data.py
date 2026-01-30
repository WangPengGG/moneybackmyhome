"""Options data tools using yfinance and local Greeks calculation."""

import logging
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import yfinance as yf
from langchain_core.tools import tool
from scipy.stats import norm

from src.models.analysis import OptionContract, OptionsChain

logger = logging.getLogger(__name__)


def _safe_decimal(value: Any) -> Decimal | None:
    """Safely convert a value to Decimal."""
    if value is None or (isinstance(value, float) and (value != value)):
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


def black_scholes_greeks(
    spot: float,
    strike: float,
    time_to_expiry: float,  # in years
    volatility: float,  # annualized, as decimal (e.g., 0.30 for 30%)
    risk_free_rate: float = 0.05,
    option_type: str = "call"
) -> dict:
    """Calculate Black-Scholes Greeks for an option.

    Args:
        spot: Current stock price
        strike: Option strike price
        time_to_expiry: Time to expiration in years
        volatility: Implied volatility as decimal
        risk_free_rate: Risk-free interest rate as decimal
        option_type: "call" or "put"

    Returns:
        Dictionary with option price and Greeks (delta, gamma, theta, vega, rho)
    """
    if time_to_expiry <= 0:
        # Option expired
        intrinsic = max(0, spot - strike) if option_type == "call" else max(0, strike - spot)
        return {
            "price": intrinsic,
            "delta": 1.0 if (option_type == "call" and spot > strike) else 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
        }

    sqrt_t = math.sqrt(time_to_expiry)
    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
        volatility * sqrt_t
    )
    d2 = d1 - volatility * sqrt_t

    # Standard normal CDF and PDF
    n_d1 = norm.cdf(d1)
    n_d2 = norm.cdf(d2)
    n_prime_d1 = norm.pdf(d1)

    # Discount factor
    discount = math.exp(-risk_free_rate * time_to_expiry)

    if option_type == "call":
        price = spot * n_d1 - strike * discount * n_d2
        delta = n_d1
        rho = strike * time_to_expiry * discount * n_d2 / 100
    else:  # put
        n_minus_d1 = norm.cdf(-d1)
        n_minus_d2 = norm.cdf(-d2)
        price = strike * discount * n_minus_d2 - spot * n_minus_d1
        delta = n_d1 - 1
        rho = -strike * time_to_expiry * discount * n_minus_d2 / 100

    # Common Greeks
    gamma = n_prime_d1 / (spot * volatility * sqrt_t)
    theta = (
        -(spot * n_prime_d1 * volatility) / (2 * sqrt_t)
        - risk_free_rate * strike * discount * n_d2
        if option_type == "call"
        else -(spot * n_prime_d1 * volatility) / (2 * sqrt_t)
        + risk_free_rate * strike * discount * norm.cdf(-d2)
    )
    # Theta per day
    theta = theta / 365
    vega = spot * n_prime_d1 * sqrt_t / 100  # Per 1% change in IV

    return {
        "price": round(price, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
    }


@tool
def get_options_chain(symbol: str, expiration_date: str | None = None) -> dict:
    """Get the options chain for a given stock symbol.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL")
        expiration_date: Optional specific expiration date (YYYY-MM-DD format).
                        If not provided, returns the nearest expiration.

    Returns:
        Dictionary containing calls and puts with their contract details.
    """
    try:
        ticker = yf.Ticker(symbol.upper())

        # Get available expiration dates
        expirations = ticker.options
        if not expirations:
            return {"error": f"No options available for {symbol}"}

        # Select expiration date
        if expiration_date:
            if expiration_date not in expirations:
                return {
                    "error": f"Expiration {expiration_date} not available",
                    "available_expirations": list(expirations),
                }
            selected_exp = expiration_date
        else:
            selected_exp = expirations[0]  # Nearest expiration

        # Fetch options chain
        chain = ticker.option_chain(selected_exp)

        # Process calls
        calls = []
        for _, row in chain.calls.iterrows():
            contract = OptionContract(
                contract_symbol=row.get("contractSymbol", ""),
                strike=_safe_decimal(row.get("strike")) or Decimal("0"),
                expiration=date.fromisoformat(selected_exp),
                option_type="call",
                last_price=_safe_decimal(row.get("lastPrice")),
                bid=_safe_decimal(row.get("bid")),
                ask=_safe_decimal(row.get("ask")),
                volume=_safe_int(row.get("volume")),
                open_interest=_safe_int(row.get("openInterest")),
                implied_volatility=_safe_decimal(row.get("impliedVolatility")),
            )
            calls.append(contract.model_dump(mode="json"))

        # Process puts
        puts = []
        for _, row in chain.puts.iterrows():
            contract = OptionContract(
                contract_symbol=row.get("contractSymbol", ""),
                strike=_safe_decimal(row.get("strike")) or Decimal("0"),
                expiration=date.fromisoformat(selected_exp),
                option_type="put",
                last_price=_safe_decimal(row.get("lastPrice")),
                bid=_safe_decimal(row.get("bid")),
                ask=_safe_decimal(row.get("ask")),
                volume=_safe_int(row.get("volume")),
                open_interest=_safe_int(row.get("openInterest")),
                implied_volatility=_safe_decimal(row.get("impliedVolatility")),
            )
            puts.append(contract.model_dump(mode="json"))

        options_chain = OptionsChain(
            symbol=symbol.upper(),
            expiration_dates=[date.fromisoformat(e) for e in expirations],
            calls=[OptionContract(**c) for c in calls],
            puts=[OptionContract(**p) for p in puts],
        )

        return {
            "symbol": symbol.upper(),
            "selected_expiration": selected_exp,
            "available_expirations": list(expirations),
            "calls_count": len(calls),
            "puts_count": len(puts),
            "calls": calls,
            "puts": puts,
        }

    except Exception as e:
        logger.error(f"Error fetching options chain for {symbol}: {e}")
        return {"error": str(e)}


@tool
def calculate_option_greeks(
    symbol: str,
    strike: float,
    expiration_date: str,
    option_type: str = "call",
    risk_free_rate: float = 0.05
) -> dict:
    """Calculate Greeks for a specific option contract.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL")
        strike: The option strike price
        expiration_date: Expiration date in YYYY-MM-DD format
        option_type: "call" or "put"
        risk_free_rate: Risk-free interest rate (default 5%)

    Returns:
        Dictionary containing option price and Greeks (delta, gamma, theta, vega, rho).
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        spot_price = info.get("regularMarketPrice")

        if not spot_price:
            return {"error": f"Could not get current price for {symbol}"}

        # Get implied volatility from options chain
        chain = ticker.option_chain(expiration_date)
        options_df = chain.calls if option_type == "call" else chain.puts

        # Find the specific contract
        contract = options_df[options_df["strike"] == strike]
        if contract.empty:
            return {"error": f"No option found with strike {strike}"}

        iv = contract.iloc[0].get("impliedVolatility", 0.3)  # Default to 30% if not available
        if iv is None or (isinstance(iv, float) and iv != iv):  # NaN check
            iv = 0.3

        # Calculate time to expiry
        exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        today = date.today()
        days_to_expiry = (exp_date - today).days
        time_to_expiry = max(days_to_expiry / 365, 0.001)  # Avoid division by zero

        # Calculate Greeks using Black-Scholes
        greeks = black_scholes_greeks(
            spot=float(spot_price),
            strike=strike,
            time_to_expiry=time_to_expiry,
            volatility=float(iv),
            risk_free_rate=risk_free_rate,
            option_type=option_type,
        )

        return {
            "symbol": symbol.upper(),
            "strike": strike,
            "expiration": expiration_date,
            "option_type": option_type,
            "spot_price": round(float(spot_price), 2),
            "implied_volatility": round(float(iv) * 100, 2),  # As percentage
            "days_to_expiry": days_to_expiry,
            **greeks,
        }

    except Exception as e:
        logger.error(f"Error calculating Greeks for {symbol} option: {e}")
        return {"error": str(e)}


@tool
def get_option_expirations(symbol: str) -> dict:
    """Get available option expiration dates for a symbol.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL")

    Returns:
        Dictionary containing list of available expiration dates.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        expirations = ticker.options

        if not expirations:
            return {"error": f"No options available for {symbol}"}

        return {
            "symbol": symbol.upper(),
            "expiration_dates": list(expirations),
            "count": len(expirations),
        }

    except Exception as e:
        logger.error(f"Error fetching option expirations for {symbol}: {e}")
        return {"error": str(e)}


@tool
def find_options_by_delta(
    symbol: str,
    target_delta: float,
    option_type: str = "call",
    expiration_date: str | None = None
) -> dict:
    """Find options near a target delta value.

    Args:
        symbol: The stock ticker symbol
        target_delta: Target delta value (0.0 to 1.0 for calls, -1.0 to 0.0 for puts)
        option_type: "call" or "put"
        expiration_date: Optional expiration date (YYYY-MM-DD). Uses nearest if not specified.

    Returns:
        Dictionary containing options near the target delta.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        spot_price = info.get("regularMarketPrice")

        if not spot_price:
            return {"error": f"Could not get current price for {symbol}"}

        expirations = ticker.options
        if not expirations:
            return {"error": f"No options available for {symbol}"}

        selected_exp = expiration_date if expiration_date in expirations else expirations[0]
        chain = ticker.option_chain(selected_exp)
        options_df = chain.calls if option_type == "call" else chain.puts

        # Calculate time to expiry
        exp_date = datetime.strptime(selected_exp, "%Y-%m-%d").date()
        today = date.today()
        time_to_expiry = max((exp_date - today).days / 365, 0.001)

        # Calculate delta for each strike and find closest to target
        results = []
        for _, row in options_df.iterrows():
            strike = row.get("strike")
            iv = row.get("impliedVolatility", 0.3)
            if iv is None or (isinstance(iv, float) and iv != iv):
                iv = 0.3

            greeks = black_scholes_greeks(
                spot=float(spot_price),
                strike=float(strike),
                time_to_expiry=time_to_expiry,
                volatility=float(iv),
                option_type=option_type,
            )

            results.append({
                "strike": float(strike),
                "delta": greeks["delta"],
                "delta_diff": abs(greeks["delta"] - target_delta),
                "implied_volatility": round(float(iv) * 100, 2),
                "last_price": float(row.get("lastPrice", 0) or 0),
                "bid": float(row.get("bid", 0) or 0),
                "ask": float(row.get("ask", 0) or 0),
                **greeks,
            })

        # Sort by closest to target delta
        results.sort(key=lambda x: x["delta_diff"])

        return {
            "symbol": symbol.upper(),
            "target_delta": target_delta,
            "option_type": option_type,
            "expiration": selected_exp,
            "spot_price": round(float(spot_price), 2),
            "closest_options": results[:5],  # Return top 5 closest
        }

    except Exception as e:
        logger.error(f"Error finding options by delta for {symbol}: {e}")
        return {"error": str(e)}
