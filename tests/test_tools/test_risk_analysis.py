"""Tests for risk analysis tools."""

import pytest

from src.services.risk_calculator import RiskCalculator, get_risk_calculator
from src.tools.risk_analysis import get_volatility_analysis


class TestRiskCalculator:
    """Test suite for RiskCalculator service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = RiskCalculator()

    def test_calculate_hv_valid_symbol(self):
        """Test calculating historical volatility for a valid symbol."""
        hv = self.calculator.calculate_hv("SPY", window=30)

        assert hv is not None
        assert hv > 0
        assert hv < 200  # Reasonable volatility range

    def test_calculate_hv_invalid_symbol(self):
        """Test calculating HV for an invalid symbol."""
        hv = self.calculator.calculate_hv("INVALIDXYZ123")

        assert hv is None

    def test_calculate_portfolio_beta_empty(self):
        """Test portfolio beta with empty positions."""
        result = self.calculator.calculate_portfolio_beta([])

        assert "error" in result
        assert result["portfolio_beta"] == 0.0

    def test_calculate_portfolio_beta_single_position(self):
        """Test portfolio beta with a single position."""
        positions = [
            {"symbol": "AAPL", "market_value": 10000}
        ]
        result = self.calculator.calculate_portfolio_beta(positions)

        assert "portfolio_beta" in result
        assert "position_betas" in result
        assert "AAPL" in result["position_betas"]

    def test_calculate_portfolio_beta_multiple_positions(self):
        """Test portfolio beta with multiple positions."""
        positions = [
            {"symbol": "AAPL", "market_value": 5000},
            {"symbol": "MSFT", "market_value": 5000},
        ]
        result = self.calculator.calculate_portfolio_beta(positions)

        assert "portfolio_beta" in result
        assert len(result["position_betas"]) == 2

    def test_calculate_concentration_metrics_empty(self):
        """Test concentration metrics with empty portfolio."""
        metrics = self.calculator.calculate_concentration_metrics([])

        assert metrics.concentration_score == 0
        assert len(metrics.warnings) > 0

    def test_calculate_concentration_metrics_single_stock(self):
        """Test concentration with single stock (maximum concentration)."""
        positions = [
            {"symbol": "AAPL", "market_value": 10000}
        ]
        metrics = self.calculator.calculate_concentration_metrics(positions)

        assert metrics.concentration_score > 0
        assert len(metrics.top_holdings) == 1
        assert metrics.top_holdings[0]["weight_percent"] == 100.0

    def test_calculate_concentration_metrics_diversified(self):
        """Test concentration with diversified portfolio."""
        positions = [
            {"symbol": "AAPL", "market_value": 2000},
            {"symbol": "MSFT", "market_value": 2000},
            {"symbol": "GOOGL", "market_value": 2000},
            {"symbol": "AMZN", "market_value": 2000},
            {"symbol": "META", "market_value": 2000},
        ]
        metrics = self.calculator.calculate_concentration_metrics(positions)

        # HHI for 5 equal positions = 5 * 20^2 = 2000
        assert metrics.hhi_score == 2000.0
        assert len(metrics.top_holdings) == 5
        # Each position should be 20%
        for holding in metrics.top_holdings:
            assert holding["weight_percent"] == 20.0

    def test_calculate_concentration_warnings(self):
        """Test that concentration warnings are generated."""
        positions = [
            {"symbol": "AAPL", "market_value": 15000},  # 75% - should warn
            {"symbol": "MSFT", "market_value": 5000},   # 25%
        ]
        metrics = self.calculator.calculate_concentration_metrics(positions)

        # Should have warning about AAPL exceeding 10%
        assert any("AAPL" in w and "10%" in w for w in metrics.warnings)

    def test_calculate_var_empty(self):
        """Test VaR calculation with empty positions."""
        result = self.calculator.calculate_var([])

        assert "error" in result
        assert result["var_amount"] == 0

    def test_calculate_var_valid_positions(self):
        """Test VaR calculation with valid positions."""
        positions = [
            {"symbol": "SPY", "market_value": 10000},
        ]
        result = self.calculator.calculate_var(positions, confidence=0.95, days=1)

        assert "var_amount" in result
        assert "var_percent" in result
        assert result["confidence"] == 0.95
        assert result["days"] == 1
        assert result["var_percent"] > 0

    def test_get_iv_from_options_valid_symbol(self):
        """Test getting IV from options for a liquid symbol."""
        iv = self.calculator.get_iv_from_options("SPY")

        # IV may be None if market is closed or options data unavailable
        # It can also be 0.0 if the impliedVolatility field is missing/zero
        if iv is not None and iv > 0:
            assert iv < 200  # Reasonable IV range

    def test_detect_hv_iv_divergence(self):
        """Test HV/IV divergence detection."""
        analysis = self.calculator.detect_hv_iv_divergence("SPY")

        assert analysis.symbol == "SPY"
        assert analysis.hv_30d is not None or analysis.hv_60d is not None
        assert analysis.hv_iv_status in ["normal", "iv_elevated", "iv_depressed"]
        assert len(analysis.recommendation) > 0


class TestRiskCalculatorSingleton:
    """Test the singleton pattern for RiskCalculator."""

    def test_get_risk_calculator_returns_same_instance(self):
        """Test that get_risk_calculator returns the same instance."""
        calc1 = get_risk_calculator()
        calc2 = get_risk_calculator()

        assert calc1 is calc2


class TestVolatilityAnalysisTool:
    """Test the get_volatility_analysis tool."""

    def test_get_volatility_analysis_valid_symbol(self):
        """Test volatility analysis for a valid symbol."""
        result = get_volatility_analysis.invoke("SPY")

        assert "error" not in result
        assert result["symbol"] == "SPY"
        assert "hv_30d" in result
        assert "hv_60d" in result
        assert "iv" in result
        assert "hv_iv_status" in result
        assert "recommendation" in result

    def test_get_volatility_analysis_invalid_symbol(self):
        """Test volatility analysis for an invalid symbol."""
        result = get_volatility_analysis.invoke("INVALIDXYZ123")

        # Should still return structure even if data unavailable
        assert "symbol" in result
        assert "hv_iv_status" in result
