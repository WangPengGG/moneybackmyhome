"""Portfolio business logic service."""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import PositionDB
from src.models.portfolio import (
    AssetType,
    Position,
    PositionCreate,
    PositionUpdate,
    PositionWithMarketData,
    PortfolioSummary,
)
from src.tools.market_data import get_stock_price

logger = logging.getLogger(__name__)


def _decimal(value) -> Decimal:
    """Convert value to Decimal safely."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class PortfolioService:
    """Service for portfolio operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_positions(self) -> list[Position]:
        """Get all positions without market data."""
        result = await self.session.execute(select(PositionDB))
        positions = result.scalars().all()

        return [
            Position(
                id=p.id,
                symbol=p.symbol,
                asset_type=p.asset_type,
                quantity=p.quantity,
                average_cost=p.average_cost,
                target_price=p.target_price,
                stop_loss=p.stop_loss,
                notes=p.notes,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in positions
        ]

    async def get_position_by_symbol(self, symbol: str) -> Position | None:
        """Get a specific position by symbol."""
        result = await self.session.execute(
            select(PositionDB).where(PositionDB.symbol == symbol.upper())
        )
        pos = result.scalar_one_or_none()

        if not pos:
            return None

        return Position(
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
        )

    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Get portfolio summary with market data."""
        result = await self.session.execute(select(PositionDB))
        positions = result.scalars().all()

        positions_with_data = []
        total_value = Decimal("0")
        total_cost = Decimal("0")

        for pos in positions:
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
                    market_value=cost_basis,
                )
                total_value += cost_basis
                total_cost += cost_basis

            positions_with_data.append(position_data)

        total_pnl = total_value - total_cost
        total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else Decimal("0")

        return PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            positions_count=len(positions_with_data),
            positions=positions_with_data,
        )

    async def create_position(self, data: PositionCreate) -> Position:
        """Create a new position."""
        position = PositionDB(
            symbol=data.symbol.upper(),
            asset_type=data.asset_type,
            quantity=data.quantity,
            average_cost=data.average_cost,
            target_price=data.target_price,
            stop_loss=data.stop_loss,
            notes=data.notes,
        )

        self.session.add(position)
        await self.session.flush()
        await self.session.refresh(position)

        return Position(
            id=position.id,
            symbol=position.symbol,
            asset_type=position.asset_type,
            quantity=position.quantity,
            average_cost=position.average_cost,
            target_price=position.target_price,
            stop_loss=position.stop_loss,
            notes=position.notes,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )

    async def update_position(self, symbol: str, data: PositionUpdate) -> Position | None:
        """Update an existing position."""
        result = await self.session.execute(
            select(PositionDB).where(PositionDB.symbol == symbol.upper())
        )
        position = result.scalar_one_or_none()

        if not position:
            return None

        if data.quantity is not None:
            position.quantity = data.quantity
        if data.average_cost is not None:
            position.average_cost = data.average_cost
        if data.target_price is not None:
            position.target_price = data.target_price
        if data.stop_loss is not None:
            position.stop_loss = data.stop_loss
        if data.notes is not None:
            position.notes = data.notes

        await self.session.flush()
        await self.session.refresh(position)

        return Position(
            id=position.id,
            symbol=position.symbol,
            asset_type=position.asset_type,
            quantity=position.quantity,
            average_cost=position.average_cost,
            target_price=position.target_price,
            stop_loss=position.stop_loss,
            notes=position.notes,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )

    async def delete_position(self, symbol: str) -> bool:
        """Delete a position."""
        result = await self.session.execute(
            select(PositionDB).where(PositionDB.symbol == symbol.upper())
        )
        position = result.scalar_one_or_none()

        if not position:
            return False

        await self.session.delete(position)
        return True
