"""API routes."""

from .watchlist import router as watchlist_router
from .screening import router as screening_router
from .spinoffs import router as spinoffs_router

__all__ = ["watchlist_router", "screening_router", "spinoffs_router"]

