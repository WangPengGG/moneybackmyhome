"""LangChain tools for Trading Assistant."""

from src.tools.market_data import (
    calculate_returns,
    compare_stocks,
    get_historical_prices,
    get_multiple_stock_prices,
    get_stock_info,
    get_stock_price,
)
from src.tools.options_data import (
    calculate_option_greeks,
    find_options_by_delta,
    get_option_expirations,
    get_options_chain,
)
from src.tools.portfolio import (
    add_position,
    get_portfolio,
    get_portfolio_symbols,
    get_position,
    remove_position,
    update_position,
)

# All tools available for agents
ALL_TOOLS = [
    # Market data tools
    get_stock_price,
    get_stock_info,
    get_historical_prices,
    get_multiple_stock_prices,
    calculate_returns,
    compare_stocks,
    # Options tools
    get_options_chain,
    calculate_option_greeks,
    get_option_expirations,
    find_options_by_delta,
    # Portfolio tools
    get_portfolio,
    get_position,
    add_position,
    update_position,
    remove_position,
    get_portfolio_symbols,
]

__all__ = [
    # Market data
    "get_stock_price",
    "get_stock_info",
    "get_historical_prices",
    "get_multiple_stock_prices",
    "calculate_returns",
    "compare_stocks",
    # Options
    "get_options_chain",
    "calculate_option_greeks",
    "get_option_expirations",
    "find_options_by_delta",
    # Portfolio
    "get_portfolio",
    "get_position",
    "add_position",
    "update_position",
    "remove_position",
    "get_portfolio_symbols",
    # Collection
    "ALL_TOOLS",
]
