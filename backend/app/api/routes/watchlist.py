"""Watchlist API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.db.database import get_db
from app.db.repositories import WatchlistRepository, NoteRepository
from app.models.watchlist import WatchlistItem, Note

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistItemCreate(BaseModel):
    """Request model for creating watchlist item."""
    symbol: str = Field(..., min_length=1, max_length=10)
    target_price: Optional[float] = Field(None, gt=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{1,5}(\.[A-Z])?$", v):
            if not re.match(r"^[A-Z]{1,5}-[A-Z]$", v):
                raise ValueError(f"Invalid symbol: {v}")
        return v


class NoteCreate(BaseModel):
    """Request model for creating a note."""
    content: str = Field(..., min_length=1, max_length=5000)


@router.get("")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get all watchlist items."""
    repo = WatchlistRepository(db)
    items = await repo.get_all()
    return [item.model_dump() for item in items]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    item: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a stock to watchlist."""
    repo = WatchlistRepository(db)
    
    # Check if already exists
    existing = await repo.get_by_symbol(item.symbol)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{item.symbol} already in watchlist",
        )
    
    watchlist_item = WatchlistItem(
        symbol=item.symbol,
        target_price=item.target_price,
    )
    result = await repo.add(watchlist_item)
    return result.model_dump()


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a stock from watchlist."""
    repo = WatchlistRepository(db)
    item = await repo.get_by_symbol(symbol.upper())
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{symbol} not in watchlist",
        )
    
    await repo.remove(item.id)


@router.get("/{symbol}/notes")
async def get_notes(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get notes for a stock."""
    repo = NoteRepository(db)
    notes = await repo.get_by_symbol(symbol.upper())
    return [note.model_dump() for note in notes]


@router.post("/{symbol}/notes", status_code=status.HTTP_201_CREATED)
async def add_note(
    symbol: str,
    note: NoteCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a stock."""
    repo = NoteRepository(db)
    new_note = Note(symbol=symbol.upper(), content=note.content)
    result = await repo.add(new_note)
    return result.model_dump()

