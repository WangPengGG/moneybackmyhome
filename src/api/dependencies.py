"""FastAPI dependencies."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import async_session_factory
from src.services.portfolio_service import PortfolioService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_portfolio_service(
    session: AsyncSession,
) -> PortfolioService:
    """Dependency to get portfolio service."""
    return PortfolioService(session)
