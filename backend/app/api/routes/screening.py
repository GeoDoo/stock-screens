"""Screening API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.screening import ScreeningService, PREDEFINED_SCREENS

router = APIRouter(prefix="/api/screening", tags=["screening"])


class FilterCondition(BaseModel):
    """A single filter condition."""
    field: str
    operator: str = Field(..., pattern=r"^(<|<=|>|>=|==|!=)$")
    value: float


class ScreenRequest(BaseModel):
    """Request model for custom screening."""
    filters: list[FilterCondition]


@router.get("/screens")
async def get_available_screens():
    """Get list of available predefined screens."""
    service = ScreeningService()
    return service.get_available_screens()


@router.get("/screens/{screen_id}")
async def get_screen_details(screen_id: str):
    """Get details of a predefined screen."""
    if screen_id not in PREDEFINED_SCREENS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screen '{screen_id}' not found",
        )
    
    screen = PREDEFINED_SCREENS[screen_id]
    return {
        "id": screen_id,
        "name": screen["name"],
        "description": screen["description"],
        "filters": screen["filters"],
    }

