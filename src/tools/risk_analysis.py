"""Risk analysis tools for agent access."""

import logging
from dataclasses import asdict
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select

from src.db import PositionDB, get_session
from src.services.risk_calculator import get_risk_calculator
from src.tools.market_data import get_stock_price

logger = logging.getLogger(__name__)


def _decimal(value) -> Decimal:
    """Convert value to Decimal safely."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


async def _get_positions_with_market_value() -> list[dict]:
    """Fetch all positions with current market values."""
    async with get_session() as session:
        result = await session.execute(select(PositionDB))
        positions_db = result.scalars().all()

        positions = []
        for pos in positions_db:
            quote = get_stock_price.invoke(pos.symbol)
            if "error" not in quote:
                current_price = _decimal(quote.get("price", 0))
                market_value = float(current_price * pos.quantity)
            else:
                market_value = float(pos.average_cost * pos.quantity)

            positions.append({
                "symbol": pos.symbol,
                "quantity": float(pos.quantity),
                "average_cost": float(pos.average_cost),
                "market_value": market_value,
            })

        return positions


@tool
async def analyze_portfolio_risk() -> dict:
    """Comprehensive portfolio risk assessment.

    Analyzes the portfolio for overall risk metrics including beta,
    volatility, and Value at Risk.

    Returns:
        Dictionary containing:
        - portfolio_beta: Beta vs SPY
        - portfolio_volatility: Annualized volatility percentage
        - var_95: 1-day Value at Risk at 95% confidence
        - risk_level: "low", "moderate", or "high"
        - warnings: List of risk alerts
    """
    try:
        positions = await _get_positions_with_market_value()

        if not positions:
            return {
                "error": "No positions in portfolio",
                "risk_level": "unknown",
                "warnings": ["Portfolio is empty - add positions to analyze risk"],
            }

        calculator = get_risk_calculator()

        # Calculate risk metrics
        beta_result = calculator.calculate_portfolio_beta(positions)
        vol_result = calculator.calculate_portfolio_volatility(positions)
        var_result = calculator.calculate_var(positions, confidence=0.95, days=1)

        portfolio_beta = beta_result.get("portfolio_beta", 0)
        portfolio_volatility = vol_result.get("annualized_volatility", 0)
        var_percent = var_result.get("var_percent", 0)
        var_amount = var_result.get("var_amount", 0)

        # Determine risk level
        warnings = []
        if portfolio_beta > 1.3:
            warnings.append(f"High beta ({portfolio_beta:.2f}) - portfolio is more volatile than market")
        elif portfolio_beta < 0.7:
            warnings.append(f"Low beta ({portfolio_beta:.2f}) - portfolio is defensive")

        if portfolio_volatility > 30:
            warnings.append(f"High volatility ({portfolio_volatility:.1f}%) - significant price swings expected")
        elif portfolio_volatility > 20:
            warnings.append(f"Moderate volatility ({portfolio_volatility:.1f}%)")

        if var_percent > 3:
            risk_level = "high"
            warnings.append(f"High daily VaR ({var_percent:.2f}%) - potential for significant losses")
        elif var_percent > 2:
            risk_level = "moderate"
        else:
            risk_level = "low"

        total_value = sum(p.get("market_value", 0) for p in positions)

        return {
            "portfolio_beta": portfolio_beta,
            "portfolio_volatility": portfolio_volatility,
            "var_95_percent": round(var_percent, 2),
            "var_95_amount": round(var_amount, 2),
            "risk_level": risk_level,
            "portfolio_value": round(total_value, 2),
            "positions_count": len(positions),
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(f"Error in analyze_portfolio_risk: {e}")
        return {"error": str(e)}


@tool
async def get_concentration_risk() -> dict:
    """Analyze portfolio concentration risk.

    Detects single-stock concentration and sector concentration issues.

    Returns:
        Dictionary containing:
        - top_holdings: List of holdings with weight percentages
        - sector_allocation: Dict of sector to weight percentage
        - concentration_score: 0-100 (higher = more concentrated)
        - warnings: List of concentration warnings
    """
    try:
        positions = await _get_positions_with_market_value()

        if not positions:
            return {
                "error": "No positions in portfolio",
                "concentration_score": 0,
                "warnings": ["Portfolio is empty"],
            }

        calculator = get_risk_calculator()
        metrics = calculator.calculate_concentration_metrics(positions)

        return {
            "top_holdings": metrics.top_holdings,
            "sector_allocation": metrics.sector_allocation,
            "concentration_score": metrics.concentration_score,
            "hhi_score": metrics.hhi_score,
            "warnings": metrics.warnings,
            "interpretation": _interpret_concentration(metrics.concentration_score),
        }

    except Exception as e:
        logger.error(f"Error in get_concentration_risk: {e}")
        return {"error": str(e)}


def _interpret_concentration(score: float) -> str:
    """Interpret concentration score."""
    if score < 20:
        return "Well diversified portfolio"
    elif score < 40:
        return "Moderately concentrated portfolio"
    elif score < 60:
        return "Concentrated portfolio - consider diversifying"
    else:
        return "Highly concentrated portfolio - significant single-stock risk"


@tool
async def calculate_portfolio_beta(benchmark: str = "SPY") -> dict:
    """Calculate portfolio beta vs a benchmark.

    Beta measures how much the portfolio moves relative to the market.
    Beta > 1 means more volatile than market, < 1 means less volatile.

    Args:
        benchmark: Ticker symbol for benchmark (default SPY)

    Returns:
        Dictionary containing:
        - portfolio_beta: Weighted average beta
        - position_betas: Dict of symbol to individual beta
        - benchmark: The benchmark used
    """
    try:
        positions = await _get_positions_with_market_value()

        if not positions:
            return {
                "error": "No positions in portfolio",
                "portfolio_beta": 0,
                "position_betas": {},
            }

        calculator = get_risk_calculator()
        result = calculator.calculate_portfolio_beta(positions, benchmark=benchmark.upper())

        # Add interpretation
        beta = result.get("portfolio_beta", 0)
        if beta > 1.2:
            interpretation = f"Portfolio is {((beta - 1) * 100):.0f}% more volatile than {benchmark}"
        elif beta < 0.8:
            interpretation = f"Portfolio is {((1 - beta) * 100):.0f}% less volatile than {benchmark}"
        else:
            interpretation = f"Portfolio moves roughly in line with {benchmark}"

        result["interpretation"] = interpretation
        return result

    except Exception as e:
        logger.error(f"Error in calculate_portfolio_beta: {e}")
        return {"error": str(e)}


@tool
def get_volatility_analysis(symbol: str) -> dict:
    """Analyze volatility for a single stock.

    Compares historical volatility (HV) with implied volatility (IV)
    to determine if options are expensive or cheap.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary containing:
        - hv_30d: 30-day historical volatility
        - hv_60d: 60-day historical volatility
        - iv: Current implied volatility from options
        - hv_iv_status: "normal", "iv_elevated", or "iv_depressed"
        - recommendation: Trading recommendation based on vol analysis
    """
    try:
        calculator = get_risk_calculator()
        analysis = calculator.detect_hv_iv_divergence(symbol.upper())

        return {
            "symbol": analysis.symbol,
            "hv_30d": analysis.hv_30d,
            "hv_60d": analysis.hv_60d,
            "iv": analysis.iv,
            "hv_iv_status": analysis.hv_iv_status,
            "recommendation": analysis.recommendation,
        }

    except Exception as e:
        logger.error(f"Error in get_volatility_analysis: {e}")
        return {"error": str(e)}


@tool
async def check_risk_alerts() -> dict:
    """Check portfolio for any active risk warnings.

    Scans the portfolio for various risk conditions including
    concentration, high beta, volatility spikes, and stop loss breaches.

    Returns:
        Dictionary containing:
        - alerts: List of {level: "warning"|"critical", message: str}
        - alert_count: Number of active alerts
    """
    try:
        positions = await _get_positions_with_market_value()

        if not positions:
            return {
                "alerts": [{"level": "warning", "message": "Portfolio is empty"}],
                "alert_count": 1,
            }

        calculator = get_risk_calculator()
        alerts = []

        # Check concentration
        concentration = calculator.calculate_concentration_metrics(positions)
        for warning in concentration.warnings:
            if "exceeds 10%" in warning:
                alerts.append({"level": "critical", "message": warning})
            else:
                alerts.append({"level": "warning", "message": warning})

        # Check beta
        beta_result = calculator.calculate_portfolio_beta(positions)
        portfolio_beta = beta_result.get("portfolio_beta", 1)
        if portfolio_beta > 1.5:
            alerts.append({
                "level": "critical",
                "message": f"Very high portfolio beta ({portfolio_beta:.2f}) - extreme market sensitivity"
            })
        elif portfolio_beta > 1.3:
            alerts.append({
                "level": "warning",
                "message": f"High portfolio beta ({portfolio_beta:.2f}) - elevated market risk"
            })

        # Check overall volatility
        vol_result = calculator.calculate_portfolio_volatility(positions)
        volatility = vol_result.get("annualized_volatility", 0)
        if volatility > 35:
            alerts.append({
                "level": "critical",
                "message": f"Very high portfolio volatility ({volatility:.1f}%)"
            })
        elif volatility > 25:
            alerts.append({
                "level": "warning",
                "message": f"Elevated portfolio volatility ({volatility:.1f}%)"
            })

        # Check VaR
        var_result = calculator.calculate_var(positions)
        var_percent = var_result.get("var_percent", 0)
        if var_percent > 4:
            alerts.append({
                "level": "critical",
                "message": f"High daily VaR ({var_percent:.2f}%) - significant loss potential"
            })

        # Check for individual position stop losses
        async with get_session() as session:
            result = await session.execute(select(PositionDB))
            positions_db = result.scalars().all()

            for pos in positions_db:
                if pos.stop_loss:
                    quote = get_stock_price.invoke(pos.symbol)
                    if "error" not in quote:
                        current_price = float(quote.get("price", 0))
                        stop_loss = float(pos.stop_loss)

                        if current_price <= stop_loss:
                            alerts.append({
                                "level": "critical",
                                "message": f"{pos.symbol} has breached stop loss (${stop_loss:.2f}). Current: ${current_price:.2f}"
                            })
                        elif current_price <= stop_loss * 1.05:
                            alerts.append({
                                "level": "warning",
                                "message": f"{pos.symbol} is within 5% of stop loss (${stop_loss:.2f}). Current: ${current_price:.2f}"
                            })

        # Sort by severity
        alerts.sort(key=lambda x: 0 if x["level"] == "critical" else 1)

        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "critical_count": sum(1 for a in alerts if a["level"] == "critical"),
            "warning_count": sum(1 for a in alerts if a["level"] == "warning"),
        }

    except Exception as e:
        logger.error(f"Error in check_risk_alerts: {e}")
        return {"error": str(e)}
