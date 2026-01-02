"""Spinoff API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories import SpinoffRepository

router = APIRouter(prefix="/api/spinoffs", tags=["spinoffs"])


@router.get("")
async def get_spinoffs(db: AsyncSession = Depends(get_db)):
    """Get all tracked spinoffs."""
    repo = SpinoffRepository(db)
    spinoffs = await repo.get_all()
    return [s.model_dump() for s in spinoffs]


@router.get("/alerts")
async def get_unread_alerts(db: AsyncSession = Depends(get_db)):
    """Get unread spinoff alerts."""
    repo = SpinoffRepository(db)
    alerts = await repo.get_unread_alerts()
    return [a.model_dump() for a in alerts]


@router.post("/alerts/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark an alert as read."""
    repo = SpinoffRepository(db)
    await repo.mark_alert_read(alert_id)

