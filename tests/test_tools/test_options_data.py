"""Tests for options data tools."""

import pytest
from src.tools.options_data import (
    get_options_chain,
    get_option_expirations,
    black_scholes_greeks,
)


class TestOptionsDataTools:
    """Test suite for options data tools."""

    def test_get_option_expirations(self):
        """Test fetching option expiration dates."""
        result = get_option_expirations.invoke("AAPL")

        assert "error" not in result
        assert "expiration_dates" in result
        assert len(result["expiration_dates"]) > 0

    def test_get_options_chain(self):
        """Test fetching options chain."""
        result = get_options_chain.invoke({"symbol": "AAPL", "expiration_date": None})

        assert "error" not in result
        assert "calls" in result
        assert "puts" in result
        assert result["calls_count"] > 0

    def test_black_scholes_greeks_call(self):
        """Test Black-Scholes Greeks calculation for a call."""
        greeks = black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,  # 3 months
            volatility=0.3,
            risk_free_rate=0.05,
            option_type="call",
        )

        assert "price" in greeks
        assert "delta" in greeks
        assert "gamma" in greeks
        assert "theta" in greeks
        assert "vega" in greeks

        # ATM call delta should be around 0.5-0.6
        assert 0.4 < greeks["delta"] < 0.7

    def test_black_scholes_greeks_put(self):
        """Test Black-Scholes Greeks calculation for a put."""
        greeks = black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            volatility=0.3,
            risk_free_rate=0.05,
            option_type="put",
        )

        # ATM put delta should be around -0.4 to -0.5
        assert -0.6 < greeks["delta"] < -0.3
