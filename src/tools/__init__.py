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
from src.tools.risk_analysis import (
    analyze_portfolio_risk,
    calculate_portfolio_beta,
    check_risk_alerts,
    get_concentration_risk,
    get_volatility_analysis,
)
from src.tools.calendar import (
    get_earnings_calendar,
    get_upcoming_macro_events,
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
    # Risk analysis tools
    analyze_portfolio_risk,
    get_concentration_risk,
    calculate_portfolio_beta,
    get_volatility_analysis,
    check_risk_alerts,
    # Calendar tools
    get_upcoming_macro_events,
    get_earnings_calendar,
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
    # Risk analysis
    "analyze_portfolio_risk",
    "get_concentration_risk",
    "calculate_portfolio_beta",
    "get_volatility_analysis",
    "check_risk_alerts",
    # Calendar
    "get_upcoming_macro_events",
    "get_earnings_calendar",
    # Collection
    "ALL_TOOLS",
]
