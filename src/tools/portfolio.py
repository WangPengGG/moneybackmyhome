"""Portfolio management tools for agent access."""

import logging
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select

from src.db import PositionDB, get_session
from src.models.portfolio import (
    AssetType,
    PortfolioSummary,
    Position,
    PositionCreate,
    PositionWithMarketData,
)
from src.tools.market_data import get_stock_price

logger = logging.getLogger(__name__)


def _decimal(value) -> Decimal:
    """Convert value to Decimal safely."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


@tool
async def get_portfolio() -> dict:
    """Get the current portfolio with all positions and market data.

    Returns:
        Dictionary containing portfolio summary with positions and market values.
    """
    try:
        async with get_session() as session:
            result = await session.execute(select(PositionDB))
            positions_db = result.scalars().all()

            positions_with_data = []
            total_value = Decimal("0")
            total_cost = Decimal("0")

            for pos in positions_db:
                # Get current market data
                quote = get_stock_price.invoke(pos.symbol)

                if "error" not in quote:
                    current_price = _decimal(quote.get("price", 0))
                    market_value = current_price * pos.quantity
                    cost_basis = pos.average_cost * pos.quantity
                    unrealized_pnl = market_value - cost_basis
                    pnl_percent = (
                        (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else Decimal("0")
                    )

                    position_data = PositionWithMarketData(
                        id=pos.id,
                        symbol=pos.symbol,
                        asset_type=pos.asset_type,
                        quantity=pos.quantity,
                        average_cost=pos.average_cost,
                        target_price=pos.target_price,
                        stop_loss=pos.stop_loss,
                        notes=pos.notes,
                        created_at=pos.created_at,
                        updated_at=pos.updated_at,
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                        unrealized_pnl_percent=pnl_percent,
                        day_change=_decimal(quote.get("change")),
                        day_change_percent=_decimal(quote.get("change_percent")),
                    )

                    total_value += market_value
                    total_cost += cost_basis
                else:
                    # Fallback without market data
                    cost_basis = pos.average_cost * pos.quantity
                    position_data = PositionWithMarketData(
                        id=pos.id,
                        symbol=pos.symbol,
                        asset_type=pos.asset_type,
                        quantity=pos.quantity,
                        average_cost=pos.average_cost,
                        target_price=pos.target_price,
                        stop_loss=pos.stop_loss,
                        notes=pos.notes,
                        created_at=pos.created_at,
                        updated_at=pos.updated_at,
                        market_value=cost_basis,  # Use cost as fallback
                    )
                    total_value += cost_basis
                    total_cost += cost_basis

                positions_with_data.append(position_data)

            total_pnl = total_value - total_cost
            total_pnl_percent = (
                (total_pnl / total_cost * 100) if total_cost > 0 else Decimal("0")
            )

            summary = PortfolioSummary(
                total_value=total_value,
                total_cost=total_cost,
                total_pnl=total_pnl,
                total_pnl_percent=total_pnl_percent,
                positions_count=len(positions_with_data),
                positions=positions_with_data,
            )

            return summary.model_dump(mode="json")

    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        return {"error": str(e)}


@tool
async def get_position(symbol: str) -> dict:
    """Get details for a specific position in the portfolio.

    Args:
        symbol: The stock ticker symbol

    Returns:
        Dictionary containing position details with market data.
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                select(PositionDB).where(PositionDB.symbol == symbol.upper())
            )
            pos = result.scalar_one_or_none()

            if not pos:
                return {"error": f"No position found for {symbol}"}

            quote = get_stock_price.invoke(pos.symbol)
            current_price = _decimal(quote.get("price", 0)) if "error" not in quote else None
            market_value = (
                current_price * pos.quantity if current_price else pos.average_cost * pos.quantity
            )
            cost_basis = pos.average_cost * pos.quantity
            unrealized_pnl = market_value - cost_basis if current_price else None

            position = PositionWithMarketData(
                id=pos.id,
                symbol=pos.symbol,
                asset_type=pos.asset_type,
                quantity=pos.quantity,
                average_cost=pos.average_cost,
                target_price=pos.target_price,
                stop_loss=pos.stop_loss,
                notes=pos.notes,
                created_at=pos.created_at,
                updated_at=pos.updated_at,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=(
                    (unrealized_pnl / cost_basis * 100) if unrealized_pnl and cost_basis > 0 else None
                ),
                day_change=_decimal(quote.get("change")) if "error" not in quote else None,
                day_change_percent=_decimal(quote.get("change_percent")) if "error" not in quote else None,
            )

            return position.model_dump(mode="json")

    except Exception as e:
        logger.error(f"Error fetching position for {symbol}: {e}")
        return {"error": str(e)}


@tool
async def add_position(
    symbol: str,
    quantity: float,
    average_cost: float,
    asset_type: str = "stock",
    target_price: float | None = None,
    stop_loss: float | None = None,
    notes: str | None = None
) -> dict:
    """Add a new position to the portfolio.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL")
        quantity: Number of shares
        average_cost: Average cost per share
        asset_type: Type of asset ("stock", "etf", "option")
        target_price: Optional target price for the position
        stop_loss: Optional stop loss price
        notes: Optional notes about the position

    Returns:
        Dictionary containing the created position.
    """
    try:
        async with get_session() as session:
            # Check if position already exists
            result = await session.execute(
                select(PositionDB).where(PositionDB.symbol == symbol.upper())
            )
            existing = result.scalar_one_or_none()

            if existing:
                return {
                    "error": f"Position for {symbol} already exists. Use update_position to modify."
                }

            # Create new position
            position = PositionDB(
                symbol=symbol.upper(),
                asset_type=AssetType(asset_type),
                quantity=Decimal(str(quantity)),
                average_cost=Decimal(str(average_cost)),
                target_price=Decimal(str(target_price)) if target_price else None,
                stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                notes=notes,
            )

            session.add(position)
            await session.flush()

            return {
                "success": True,
                "message": f"Added {quantity} shares of {symbol.upper()} at ${average_cost}",
                "position_id": position.id,
            }

    except Exception as e:
        logger.error(f"Error adding position for {symbol}: {e}")
        return {"error": str(e)}


@tool
async def update_position(
    symbol: str,
    quantity: float | None = None,
    average_cost: float | None = None,
    target_price: float | None = None,
    stop_loss: float | None = None,
    notes: str | None = None
) -> dict:
    """Update an existing position in the portfolio.

    Args:
        symbol: The stock ticker symbol
        quantity: New quantity (optional)
        average_cost: New average cost (optional)
        target_price: New target price (optional, use 0 to clear)
        stop_loss: New stop loss (optional, use 0 to clear)
        notes: New notes (optional)

    Returns:
        Dictionary containing the updated position.
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                select(PositionDB).where(PositionDB.symbol == symbol.upper())
            )
            position = result.scalar_one_or_none()

            if not position:
                return {"error": f"No position found for {symbol}"}

            if quantity is not None:
                position.quantity = Decimal(str(quantity))
            if average_cost is not None:
                position.average_cost = Decimal(str(average_cost))
            if target_price is not None:
                position.target_price = Decimal(str(target_price)) if target_price > 0 else None
            if stop_loss is not None:
                position.stop_loss = Decimal(str(stop_loss)) if stop_loss > 0 else None
            if notes is not None:
                position.notes = notes

            return {
                "success": True,
                "message": f"Updated position for {symbol.upper()}",
                "position_id": position.id,
            }

    except Exception as e:
        logger.error(f"Error updating position for {symbol}: {e}")
        return {"error": str(e)}


@tool
async def remove_position(symbol: str) -> dict:
    """Remove a position from the portfolio.

    Args:
        symbol: The stock ticker symbol to remove

    Returns:
        Dictionary indicating success or error.
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                select(PositionDB).where(PositionDB.symbol == symbol.upper())
            )
            position = result.scalar_one_or_none()

            if not position:
                return {"error": f"No position found for {symbol}"}

            await session.delete(position)

            return {
                "success": True,
                "message": f"Removed position for {symbol.upper()}",
            }

    except Exception as e:
        logger.error(f"Error removing position for {symbol}: {e}")
        return {"error": str(e)}


@tool
async def get_portfolio_symbols() -> dict:
    """Get list of all symbols in the portfolio.

    Returns:
        Dictionary containing list of symbols.
    """
    try:
        async with get_session() as session:
            result = await session.execute(select(PositionDB.symbol))
            symbols = [row[0] for row in result.all()]

            return {
                "symbols": symbols,
                "count": len(symbols),
            }

    except Exception as e:
        logger.error(f"Error fetching portfolio symbols: {e}")
        return {"error": str(e)}
