"""Risk calculation service for portfolio analysis."""

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import yfinance as yf
from scipy.stats import norm

logger = logging.getLogger(__name__)


@dataclass
class ConcentrationMetrics:
    """Concentration risk metrics for a portfolio."""

    top_holdings: list[dict[str, Any]]
    sector_allocation: dict[str, float]
    hhi_score: float  # Herfindahl-Hirschman Index (0-10000)
    concentration_score: float  # Normalized 0-100
    warnings: list[str]


@dataclass
class VolatilityAnalysis:
    """Volatility analysis for a symbol."""

    symbol: str
    hv_30d: float | None
    hv_60d: float | None
    iv: float | None
    hv_iv_status: str  # "normal", "iv_elevated", "iv_depressed"
    recommendation: str


def _safe_float(value: Any) -> float | None:
    """Safely convert value to float."""
    if value is None:
        return None
    if isinstance(value, float) and (value != value):  # NaN check
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _decimal(value: Any) -> Decimal:
    """Convert value to Decimal safely."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class RiskCalculator:
    """Service for calculating portfolio risk metrics."""

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def calculate_portfolio_beta(
        self,
        positions: list[dict],
        benchmark: str = "SPY"
    ) -> dict[str, Any]:
        """Calculate portfolio beta using weighted average of individual betas.

        Args:
            positions: List of position dicts with 'symbol', 'market_value'
            benchmark: Benchmark symbol (default SPY)

        Returns:
            Dict with portfolio_beta and position_betas
        """
        if not positions:
            return {"portfolio_beta": 0.0, "position_betas": {}, "error": "No positions"}

        total_value = sum(float(p.get("market_value", 0) or 0) for p in positions)
        if total_value <= 0:
            return {"portfolio_beta": 0.0, "position_betas": {}, "error": "Zero portfolio value"}

        position_betas = {}
        weighted_beta_sum = 0.0

        for pos in positions:
            symbol = pos.get("symbol", "")
            market_value = float(pos.get("market_value", 0) or 0)
            weight = market_value / total_value if total_value > 0 else 0

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                beta = _safe_float(info.get("beta"))

                if beta is None:
                    # Calculate beta from historical returns vs benchmark
                    beta = self._calculate_beta_from_returns(symbol, benchmark)

                if beta is not None:
                    position_betas[symbol] = round(beta, 3)
                    weighted_beta_sum += beta * weight
                else:
                    position_betas[symbol] = None

            except Exception as e:
                logger.warning(f"Error getting beta for {symbol}: {e}")
                position_betas[symbol] = None

        return {
            "portfolio_beta": round(weighted_beta_sum, 3),
            "position_betas": position_betas,
            "benchmark": benchmark,
        }

    def _calculate_beta_from_returns(
        self,
        symbol: str,
        benchmark: str,
        period: str = "1y"
    ) -> float | None:
        """Calculate beta from historical returns."""
        try:
            stock = yf.Ticker(symbol)
            bench = yf.Ticker(benchmark)

            stock_hist = stock.history(period=period)
            bench_hist = bench.history(period=period)

            if len(stock_hist) < 20 or len(bench_hist) < 20:
                return None

            stock_returns = stock_hist["Close"].pct_change().dropna()
            bench_returns = bench_hist["Close"].pct_change().dropna()

            # Align dates
            common_dates = stock_returns.index.intersection(bench_returns.index)
            if len(common_dates) < 20:
                return None

            stock_returns = stock_returns.loc[common_dates]
            bench_returns = bench_returns.loc[common_dates]

            covariance = np.cov(stock_returns, bench_returns)[0, 1]
            variance = np.var(bench_returns)

            if variance == 0:
                return None

            return covariance / variance

        except Exception as e:
            logger.warning(f"Error calculating beta from returns for {symbol}: {e}")
            return None

    def calculate_portfolio_volatility(
        self,
        positions: list[dict],
        period: str = "1y"
    ) -> dict[str, Any]:
        """Calculate portfolio volatility using position weights and correlations.

        Args:
            positions: List of position dicts with 'symbol', 'market_value'
            period: Historical period for calculation

        Returns:
            Dict with annualized volatility and contribution by position
        """
        if not positions:
            return {"error": "No positions", "annualized_volatility": 0.0}

        symbols = [p.get("symbol", "") for p in positions]
        total_value = sum(float(p.get("market_value", 0) or 0) for p in positions)

        if total_value <= 0:
            return {"error": "Zero portfolio value", "annualized_volatility": 0.0}

        weights = np.array([
            float(p.get("market_value", 0) or 0) / total_value
            for p in positions
        ])

        # Get historical returns for all positions
        returns_data = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                if not hist.empty and len(hist) > 1:
                    returns_data[symbol] = hist["Close"].pct_change().dropna()
            except Exception as e:
                logger.warning(f"Error fetching history for {symbol}: {e}")

        if not returns_data:
            return {"error": "Could not fetch historical data", "annualized_volatility": 0.0}

        # Find common dates
        all_dates = None
        for symbol, returns in returns_data.items():
            if all_dates is None:
                all_dates = set(returns.index)
            else:
                all_dates = all_dates.intersection(set(returns.index))

        if not all_dates or len(all_dates) < 20:
            return {"error": "Insufficient common historical data", "annualized_volatility": 0.0}

        common_dates = sorted(list(all_dates))

        # Build returns matrix
        returns_matrix = []
        position_volatilities = {}
        for i, symbol in enumerate(symbols):
            if symbol in returns_data:
                aligned_returns = returns_data[symbol].loc[common_dates]
                returns_matrix.append(aligned_returns.values)
                position_volatilities[symbol] = round(
                    float(aligned_returns.std() * np.sqrt(252) * 100), 2
                )
            else:
                # Fallback: assume market-like volatility
                returns_matrix.append(np.zeros(len(common_dates)))
                position_volatilities[symbol] = None

        returns_matrix = np.array(returns_matrix)

        # Calculate correlation matrix and covariance matrix
        cov_matrix = np.cov(returns_matrix)

        # Portfolio variance = w' * Cov * w
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance) * np.sqrt(252)  # Annualized

        # Calculate marginal contribution to risk
        marginal_contrib = np.dot(cov_matrix, weights) / np.sqrt(portfolio_variance)
        contribution = weights * marginal_contrib
        contribution_pct = contribution / contribution.sum() * 100 if contribution.sum() > 0 else contribution

        volatility_contribution = {
            symbols[i]: round(float(contribution_pct[i]), 2)
            for i in range(len(symbols))
        }

        return {
            "annualized_volatility": round(float(portfolio_volatility * 100), 2),
            "position_volatilities": position_volatilities,
            "volatility_contribution": volatility_contribution,
            "trading_days_used": len(common_dates),
        }

    def calculate_concentration_metrics(
        self,
        positions: list[dict]
    ) -> ConcentrationMetrics:
        """Calculate portfolio concentration metrics.

        Args:
            positions: List of position dicts with 'symbol', 'market_value'

        Returns:
            ConcentrationMetrics with holdings, sectors, HHI, and warnings
        """
        if not positions:
            return ConcentrationMetrics(
                top_holdings=[],
                sector_allocation={},
                hhi_score=0,
                concentration_score=0,
                warnings=["Portfolio is empty"],
            )

        total_value = sum(float(p.get("market_value", 0) or 0) for p in positions)
        if total_value <= 0:
            return ConcentrationMetrics(
                top_holdings=[],
                sector_allocation={},
                hhi_score=0,
                concentration_score=0,
                warnings=["Portfolio has no value"],
            )

        # Calculate weights and get sector info
        holdings = []
        sector_values: dict[str, float] = {}
        warnings = []

        for pos in positions:
            symbol = pos.get("symbol", "")
            market_value = float(pos.get("market_value", 0) or 0)
            weight = (market_value / total_value * 100) if total_value > 0 else 0

            # Get sector info
            sector = "Unknown"
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                sector = info.get("sector", "Unknown") or "Unknown"
            except Exception as e:
                logger.warning(f"Error getting sector for {symbol}: {e}")

            holdings.append({
                "symbol": symbol,
                "market_value": round(market_value, 2),
                "weight_percent": round(weight, 2),
                "sector": sector,
            })

            sector_values[sector] = sector_values.get(sector, 0) + market_value

            # Check for concentration warnings
            if weight > 10:
                warnings.append(f"{symbol} exceeds 10% allocation ({weight:.1f}%)")
            elif weight > 5:
                warnings.append(f"{symbol} exceeds 5% allocation ({weight:.1f}%)")

        # Sort by weight descending
        holdings.sort(key=lambda x: x["weight_percent"], reverse=True)

        # Calculate sector allocation percentages
        sector_allocation = {
            sector: round((value / total_value * 100), 2)
            for sector, value in sector_values.items()
        }

        # Check for sector concentration
        for sector, pct in sector_allocation.items():
            if pct > 40 and sector != "Unknown":
                warnings.append(f"Sector concentration: {sector} is {pct:.1f}% of portfolio")

        # Calculate Herfindahl-Hirschman Index (HHI)
        # HHI = sum of squared market share percentages (0-10000 scale)
        weights_pct = [h["weight_percent"] for h in holdings]
        hhi = sum(w ** 2 for w in weights_pct)

        # Normalize to 0-100 concentration score
        # HHI of 10000 = single stock (100% concentration)
        # HHI of 100 = 100 equal stocks (low concentration)
        if len(holdings) == 1:
            # Single position = maximum concentration
            concentration_score = 100.0
        else:
            min_hhi = 10000 / len(holdings)
            concentration_score = min(100, max(0, (hhi - min_hhi) / (10000 - min_hhi) * 100))

        return ConcentrationMetrics(
            top_holdings=holdings[:10],  # Top 10
            sector_allocation=sector_allocation,
            hhi_score=round(hhi, 2),
            concentration_score=round(concentration_score, 2),
            warnings=warnings,
        )

    def calculate_var(
        self,
        positions: list[dict],
        confidence: float = 0.95,
        days: int = 1
    ) -> dict[str, Any]:
        """Calculate Value at Risk for the portfolio.

        Args:
            positions: List of position dicts with 'symbol', 'market_value'
            confidence: Confidence level (default 0.95 = 95%)
            days: Time horizon in days (default 1)

        Returns:
            Dict with VaR amount and percentage
        """
        vol_result = self.calculate_portfolio_volatility(positions, period="1y")

        if "error" in vol_result:
            return {"error": vol_result["error"], "var_amount": 0, "var_percent": 0}

        annualized_vol = vol_result.get("annualized_volatility", 0) / 100
        total_value = sum(float(p.get("market_value", 0) or 0) for p in positions)

        if total_value <= 0:
            return {"error": "Zero portfolio value", "var_amount": 0, "var_percent": 0}

        # Daily volatility
        daily_vol = annualized_vol / np.sqrt(252)

        # Scale for time horizon
        period_vol = daily_vol * np.sqrt(days)

        # Z-score for confidence level
        z_score = norm.ppf(confidence)

        # VaR calculation (parametric)
        var_percent = z_score * period_vol * 100
        var_amount = z_score * period_vol * total_value

        return {
            "var_amount": round(var_amount, 2),
            "var_percent": round(var_percent, 2),
            "confidence": confidence,
            "days": days,
            "portfolio_value": round(total_value, 2),
            "interpretation": f"There is a {(1-confidence)*100:.0f}% chance of losing more than ${var_amount:,.2f} ({var_percent:.2f}%) in {days} day(s)",
        }

    def calculate_hv(
        self,
        symbol: str,
        window: int = 30,
        period: str = "1y"
    ) -> float | None:
        """Calculate annualized historical volatility.

        Args:
            symbol: Stock ticker
            window: Rolling window in days (default 30)
            period: Historical period to fetch

        Returns:
            Annualized historical volatility as percentage, or None if error
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty or len(hist) < window:
                return None

            # Calculate daily returns
            daily_returns = hist["Close"].pct_change().dropna()

            # Use recent window
            recent_returns = daily_returns.tail(window)

            # Calculate standard deviation and annualize
            daily_std = recent_returns.std()
            annualized_vol = daily_std * np.sqrt(252) * 100

            return round(float(annualized_vol), 2)

        except Exception as e:
            logger.error(f"Error calculating HV for {symbol}: {e}")
            return None

    def get_iv_from_options(self, symbol: str) -> float | None:
        """Get implied volatility from near-ATM options (30-45 DTE).

        Args:
            symbol: Stock ticker

        Returns:
            Implied volatility as percentage, or None if unavailable
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            spot_price = _safe_float(info.get("regularMarketPrice"))

            if not spot_price:
                return None

            expirations = ticker.options
            if not expirations:
                return None

            # Find expiration 30-45 days out
            today = date.today()
            target_exp = None

            for exp in expirations:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                days_to_exp = (exp_date - today).days

                if 30 <= days_to_exp <= 60:
                    target_exp = exp
                    break
                elif days_to_exp > 20:
                    target_exp = exp  # Use closest if nothing in range
                    break

            if not target_exp:
                target_exp = expirations[0] if expirations else None

            if not target_exp:
                return None

            # Get options chain
            chain = ticker.option_chain(target_exp)

            # Find ATM call option
            calls = chain.calls
            if calls.empty:
                return None

            # Find strike closest to spot price
            calls["atm_diff"] = abs(calls["strike"] - spot_price)
            atm_call = calls.loc[calls["atm_diff"].idxmin()]

            iv = _safe_float(atm_call.get("impliedVolatility"))
            if iv is not None and iv > 0:
                return round(iv * 100, 2)  # Convert to percentage

            return None

        except Exception as e:
            logger.error(f"Error getting IV for {symbol}: {e}")
            return None

    def detect_hv_iv_divergence(
        self,
        symbol: str,
        threshold: float = 0.2
    ) -> VolatilityAnalysis:
        """Compare historical volatility vs implied volatility.

        Args:
            symbol: Stock ticker
            threshold: Divergence threshold (default 0.2 = 20%)

        Returns:
            VolatilityAnalysis with HV, IV, status, and recommendation
        """
        hv_30d = self.calculate_hv(symbol, window=30)
        hv_60d = self.calculate_hv(symbol, window=60)
        iv = self.get_iv_from_options(symbol)

        # Determine status
        status = "normal"
        recommendation = "Volatility appears normal"

        if hv_30d is not None and iv is not None:
            hv_ref = hv_30d
            ratio = iv / hv_ref if hv_ref > 0 else 1.0

            if ratio > (1 + threshold):
                status = "iv_elevated"
                recommendation = f"IV ({iv:.1f}%) is elevated vs HV ({hv_ref:.1f}%). Options may be expensive. Consider selling premium strategies."
            elif ratio < (1 - threshold):
                status = "iv_depressed"
                recommendation = f"IV ({iv:.1f}%) is depressed vs HV ({hv_ref:.1f}%). Options may be cheap. Consider buying options."
            else:
                recommendation = f"IV ({iv:.1f}%) is in line with HV ({hv_ref:.1f}%). Options appear fairly priced."
        elif iv is None:
            recommendation = "Could not retrieve implied volatility from options chain"
        elif hv_30d is None:
            recommendation = "Could not calculate historical volatility"

        return VolatilityAnalysis(
            symbol=symbol.upper(),
            hv_30d=hv_30d,
            hv_60d=hv_60d,
            iv=iv,
            hv_iv_status=status,
            recommendation=recommendation,
        )


# Singleton instance
_calculator: RiskCalculator | None = None


def get_risk_calculator() -> RiskCalculator:
    """Get or create the risk calculator singleton."""
    global _calculator
    if _calculator is None:
        _calculator = RiskCalculator()
    return _calculator
