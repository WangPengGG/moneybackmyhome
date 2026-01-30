"""Agent state models for LangGraph."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the orchestrator agent."""

    messages: Annotated[list, add_messages]
    current_intent: str | None
    portfolio_context: dict | None
    analysis_results: dict | None
    error: str | None


class RiskScannerState(TypedDict):
    """State for the risk scanner agent."""

    messages: Annotated[list, add_messages]
    portfolio_id: int | None
    risk_metrics: dict | None
    warnings: list[str]
    recommendations: list[str]


class DecisionSupportState(TypedDict):
    """State for the decision support agent."""

    messages: Annotated[list, add_messages]
    symbol: str | None
    analysis_type: str | None  # "buy", "sell", "hold", "size"
    market_data: dict | None
    sentiment_data: dict | None
    recommendation: dict | None


class OptionsHedgingState(TypedDict):
    """State for the options hedging agent."""

    messages: Annotated[list, add_messages]
    portfolio_greeks: dict | None
    hedging_goal: str | None  # "delta_neutral", "protect_gains", "income"
    suggested_strategies: list[dict]
