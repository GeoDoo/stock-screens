"""Repository classes for data access."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WatchlistItemDB, NoteDB, SpinoffDB, SpinoffAlertDB
from app.models.watchlist import WatchlistItem, Note
from app.models.spinoff import Spinoff, SpinoffAlert


class WatchlistRepository:
    """Repository for watchlist operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, item: WatchlistItem) -> WatchlistItem:
        """Add a stock to the watchlist."""
        db_item = WatchlistItemDB(
            symbol=item.symbol,
            target_price=item.target_price,
            alert_on_price_drop=item.alert_on_price_drop,
            alert_threshold_percent=item.alert_threshold_percent,
        )
        self.session.add(db_item)
        await self.session.commit()
        await self.session.refresh(db_item)
        
        return WatchlistItem(
            id=db_item.id,
            symbol=db_item.symbol,
            added_at=db_item.added_at,
            target_price=db_item.target_price,
            alert_on_price_drop=db_item.alert_on_price_drop,
            alert_threshold_percent=db_item.alert_threshold_percent,
        )
    
    async def get_all(self) -> List[WatchlistItem]:
        """Get all watchlist items."""
        result = await self.session.execute(select(WatchlistItemDB))
        db_items = result.scalars().all()
        
        return [
            WatchlistItem(
                id=item.id,
                symbol=item.symbol,
                added_at=item.added_at,
                target_price=item.target_price,
                alert_on_price_drop=item.alert_on_price_drop,
                alert_threshold_percent=item.alert_threshold_percent,
            )
            for item in db_items
        ]
    
    async def get_by_symbol(self, symbol: str) -> Optional[WatchlistItem]:
        """Get a watchlist item by symbol."""
        result = await self.session.execute(
            select(WatchlistItemDB).where(WatchlistItemDB.symbol == symbol)
        )
        db_item = result.scalar_one_or_none()
        
        if not db_item:
            return None
        
        return WatchlistItem(
            id=db_item.id,
            symbol=db_item.symbol,
            added_at=db_item.added_at,
            target_price=db_item.target_price,
            alert_on_price_drop=db_item.alert_on_price_drop,
            alert_threshold_percent=db_item.alert_threshold_percent,
        )
    
    async def remove(self, item_id: int) -> None:
        """Remove a stock from the watchlist."""
        await self.session.execute(
            delete(WatchlistItemDB).where(WatchlistItemDB.id == item_id)
        )
        await self.session.commit()


class NoteRepository:
    """Repository for notes operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, note: Note) -> Note:
        """Add a note."""
        db_note = NoteDB(
            symbol=note.symbol,
            content=note.content,
        )
        self.session.add(db_note)
        await self.session.commit()
        await self.session.refresh(db_note)
        
        return Note(
            id=db_note.id,
            symbol=db_note.symbol,
            content=db_note.content,
            created_at=db_note.created_at,
            updated_at=db_note.updated_at,
        )
    
    async def get_by_symbol(self, symbol: str) -> List[Note]:
        """Get all notes for a symbol."""
        result = await self.session.execute(
            select(NoteDB).where(NoteDB.symbol == symbol)
        )
        db_notes = result.scalars().all()
        
        return [
            Note(
                id=note.id,
                symbol=note.symbol,
                content=note.content,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
            for note in db_notes
        ]
    
    async def update(self, note_id: int, content: str) -> Optional[Note]:
        """Update a note's content."""
        result = await self.session.execute(
            select(NoteDB).where(NoteDB.id == note_id)
        )
        db_note = result.scalar_one_or_none()
        
        if not db_note:
            return None
        
        db_note.content = content
        db_note.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(db_note)
        
        return Note(
            id=db_note.id,
            symbol=db_note.symbol,
            content=db_note.content,
            created_at=db_note.created_at,
            updated_at=db_note.updated_at,
        )
    
    async def delete(self, note_id: int) -> None:
        """Delete a note."""
        await self.session.execute(
            delete(NoteDB).where(NoteDB.id == note_id)
        )
        await self.session.commit()


class SpinoffRepository:
    """Repository for spinoff operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, spinoff: Spinoff) -> Spinoff:
        """Add a spinoff."""
        db_spinoff = SpinoffDB(
            spinoff_symbol=spinoff.spinoff_symbol,
            spinoff_name=spinoff.spinoff_name,
            parent_symbol=spinoff.parent_symbol,
            parent_name=spinoff.parent_name,
            sec_filing_url=spinoff.sec_filing_url,
            sec_filing_date=spinoff.sec_filing_date,
            sec_filing_type=spinoff.sec_filing_type,
            announcement_date=spinoff.announcement_date,
            effective_date=spinoff.effective_date,
            record_date=spinoff.record_date,
            distribution_ratio=spinoff.distribution_ratio,
            description=spinoff.description,
            sector=spinoff.sector,
            industry=spinoff.industry,
            status=spinoff.status,
        )
        self.session.add(db_spinoff)
        await self.session.commit()
        await self.session.refresh(db_spinoff)
        
        spinoff.id = db_spinoff.id
        return spinoff
    
    async def get_all(self) -> List[Spinoff]:
        """Get all spinoffs."""
        result = await self.session.execute(select(SpinoffDB))
        return [self._to_domain(s) for s in result.scalars().all()]
    
    async def get_unread_alerts(self) -> List[SpinoffAlert]:
        """Get all unread spinoff alerts."""
        result = await self.session.execute(
            select(SpinoffAlertDB).where(SpinoffAlertDB.is_read == False)
        )
        db_alerts = result.scalars().all()
        
        return [
            SpinoffAlert(
                id=alert.id,
                spinoff_id=alert.spinoff_id,
                title=alert.title,
                message=alert.message,
                is_read=alert.is_read,
                created_at=alert.created_at,
                read_at=alert.read_at,
            )
            for alert in db_alerts
        ]
    
    async def create_alert(self, spinoff_id: int, title: str, message: str) -> SpinoffAlert:
        """Create a new spinoff alert."""
        db_alert = SpinoffAlertDB(
            spinoff_id=spinoff_id,
            title=title,
            message=message,
        )
        self.session.add(db_alert)
        await self.session.commit()
        await self.session.refresh(db_alert)
        
        return SpinoffAlert(
            id=db_alert.id,
            spinoff_id=db_alert.spinoff_id,
            title=db_alert.title,
            message=db_alert.message,
            is_read=db_alert.is_read,
            created_at=db_alert.created_at,
        )
    
    async def mark_alert_read(self, alert_id: int) -> None:
        """Mark an alert as read."""
        result = await self.session.execute(
            select(SpinoffAlertDB).where(SpinoffAlertDB.id == alert_id)
        )
        db_alert = result.scalar_one_or_none()
        
        if db_alert:
            db_alert.is_read = True
            db_alert.read_at = datetime.utcnow()
            await self.session.commit()
    
    def _to_domain(self, db_spinoff: SpinoffDB) -> Spinoff:
        """Convert DB model to domain model."""
        return Spinoff(
            id=db_spinoff.id,
            spinoff_symbol=db_spinoff.spinoff_symbol,
            spinoff_name=db_spinoff.spinoff_name,
            parent_symbol=db_spinoff.parent_symbol,
            parent_name=db_spinoff.parent_name,
            sec_filing_url=db_spinoff.sec_filing_url,
            sec_filing_date=db_spinoff.sec_filing_date.date() if db_spinoff.sec_filing_date else None,
            sec_filing_type=db_spinoff.sec_filing_type,
            announcement_date=db_spinoff.announcement_date.date() if db_spinoff.announcement_date else None,
            effective_date=db_spinoff.effective_date.date() if db_spinoff.effective_date else None,
            record_date=db_spinoff.record_date.date() if db_spinoff.record_date else None,
            distribution_ratio=db_spinoff.distribution_ratio,
            description=db_spinoff.description,
            sector=db_spinoff.sector,
            industry=db_spinoff.industry,
            status=db_spinoff.status,
            discovered_at=db_spinoff.discovered_at,
            last_updated=db_spinoff.last_updated,
        )

