"""Tests for market data tools."""

import pytest
from src.tools.market_data import get_stock_price, get_stock_info, calculate_returns


class TestMarketDataTools:
    """Test suite for market data tools."""

    def test_get_stock_price_valid_symbol(self):
        """Test fetching stock price for a valid symbol."""
        result = get_stock_price.invoke("AAPL")

        assert "error" not in result
        assert result["symbol"] == "AAPL"
        assert "price" in result
        assert float(result["price"]) > 0

    def test_get_stock_price_invalid_symbol(self):
        """Test fetching stock price for an invalid symbol."""
        result = get_stock_price.invoke("INVALIDXYZ123")

        assert "error" in result

    def test_get_stock_info_valid_symbol(self):
        """Test fetching stock info for a valid symbol."""
        result = get_stock_info.invoke("MSFT")

        assert "error" not in result
        assert result["symbol"] == "MSFT"
        assert "name" in result
        assert "sector" in result

    def test_calculate_returns(self):
        """Test calculating returns for a stock."""
        result = calculate_returns.invoke({"symbol": "SPY", "period": "1mo"})

        assert "error" not in result
        assert "total_return_percent" in result
        assert "annualized_volatility_percent" in result
        assert "max_drawdown_percent" in result
