"""API routes for Trading Assistant."""

from src.api.routes.analysis import router as analysis_router
from src.api.routes.chat import router as chat_router
from src.api.routes.portfolio import router as portfolio_router

__all__ = [
    "chat_router",
    "portfolio_router",
    "analysis_router",
]
