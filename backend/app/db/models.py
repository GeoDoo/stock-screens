"""SQLAlchemy ORM models for persistence."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.spinoff import SpinoffStatus


class WatchlistItemDB(Base):
    """Watchlist item database model."""
    
    __tablename__ = "watchlist_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    target_price = Column(Float, nullable=True)
    alert_on_price_drop = Column(Boolean, default=False)
    alert_threshold_percent = Column(Float, nullable=True)
    
    # Relationship to notes
    notes = relationship("NoteDB", back_populates="watchlist_item", cascade="all, delete-orphan")


class NoteDB(Base):
    """Note database model."""
    
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key to watchlist (optional)
    watchlist_item_id = Column(Integer, ForeignKey("watchlist_items.id"), nullable=True)
    watchlist_item = relationship("WatchlistItemDB", back_populates="notes")


class SpinoffDB(Base):
    """Spinoff database model."""
    
    __tablename__ = "spinoffs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    spinoff_symbol = Column(String(10), nullable=True, index=True)
    spinoff_name = Column(String(200), nullable=False)
    parent_symbol = Column(String(10), nullable=False, index=True)
    parent_name = Column(String(200), nullable=False)
    
    sec_filing_url = Column(String(500), nullable=True)
    sec_filing_date = Column(DateTime, nullable=True)
    sec_filing_type = Column(String(20), default="10-12B")
    
    announcement_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    record_date = Column(DateTime, nullable=True)
    
    distribution_ratio = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    
    status = Column(SQLEnum(SpinoffStatus), default=SpinoffStatus.ANNOUNCED)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to alerts
    alerts = relationship("SpinoffAlertDB", back_populates="spinoff", cascade="all, delete-orphan")


class SpinoffAlertDB(Base):
    """Spinoff alert database model."""
    
    __tablename__ = "spinoff_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    spinoff_id = Column(Integer, ForeignKey("spinoffs.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    spinoff = relationship("SpinoffDB", back_populates="alerts")

