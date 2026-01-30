"""Portfolio API endpoints."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.models.portfolio import (
    Position,
    PositionCreate,
    PositionUpdate,
    PortfolioSummary,
)
from src.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/", response_model=PortfolioSummary)
async def get_portfolio(
    session: AsyncSession = Depends(get_db_session),
) -> PortfolioSummary:
    """Get the complete portfolio with current market data.

    Returns:
        Portfolio summary with all positions and market values
    """
    service = PortfolioService(session)
    return await service.get_portfolio_summary()


@router.get("/positions", response_model=list[Position])
async def get_positions(
    session: AsyncSession = Depends(get_db_session),
) -> list[Position]:
    """Get all positions without market data (faster).

    Returns:
        List of all positions
    """
    service = PortfolioService(session)
    return await service.get_all_positions()


@router.get("/positions/{symbol}", response_model=Position)
async def get_position(
    symbol: str,
    session: AsyncSession = Depends(get_db_session),
) -> Position:
    """Get a specific position by symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Position details
    """
    service = PortfolioService(session)
    position = await service.get_position_by_symbol(symbol)

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")

    return position


@router.post("/positions", response_model=Position, status_code=201)
async def create_position(
    data: PositionCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Position:
    """Add a new position to the portfolio.

    Args:
        data: Position data

    Returns:
        Created position
    """
    service = PortfolioService(session)

    # Check if position already exists
    existing = await service.get_position_by_symbol(data.symbol)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Position already exists for {data.symbol}. Use PUT to update."
        )

    return await service.create_position(data)


@router.put("/positions/{symbol}", response_model=Position)
async def update_position(
    symbol: str,
    data: PositionUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Position:
    """Update an existing position.

    Args:
        symbol: Stock ticker symbol
        data: Fields to update

    Returns:
        Updated position
    """
    service = PortfolioService(session)
    position = await service.update_position(symbol, data)

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")

    return position


@router.delete("/positions/{symbol}", status_code=204)
async def delete_position(
    symbol: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a position from the portfolio.

    Args:
        symbol: Stock ticker symbol
    """
    service = PortfolioService(session)
    deleted = await service.delete_position(symbol)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")
