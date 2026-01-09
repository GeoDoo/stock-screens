"""
Audit Repository - SQLite persistence for assumption audit trail.

Stores and retrieves assumption change history for investment thesis tracking.
"""
from datetime import datetime
from typing import List, Optional

from app.services.database import get_connection, DEFAULT_DB_PATH
from app.models.assumption_audit import (
    AssumptionField,
    AssumptionChange,
    AuditEntry,
    AssumptionSnapshot,
)


class AuditRepository:
    """
    SQLite-based repository for assumption audit entries.
    
    Schema:
    - audit_entries: id, symbol, timestamp, note, is_initial
    - audit_changes: id, entry_id, field, old_value, new_value
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file. Defaults to stock_screens.db
        """
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema if not exists."""
        with get_connection(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS audit_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    note TEXT,
                    is_initial INTEGER NOT NULL DEFAULT 0,
                    price_at_time REAL,
                    intrinsic_value_at_time REAL,
                    pe_ratio_at_time REAL
                );
                
                CREATE TABLE IF NOT EXISTS audit_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    field TEXT NOT NULL,
                    old_value REAL,
                    new_value REAL,  -- Can be NULL when clearing an assumption
                    FOREIGN KEY (entry_id) REFERENCES audit_entries(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_entries_symbol 
                ON audit_entries(symbol);
                
                CREATE INDEX IF NOT EXISTS idx_entries_timestamp 
                ON audit_entries(timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_changes_entry 
                ON audit_changes(entry_id);
            """)
            # Migration: Add new columns if they don't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE audit_entries ADD COLUMN price_at_time REAL")
            except Exception:
                pass  # Column already exists
            try:
                conn.execute("ALTER TABLE audit_entries ADD COLUMN intrinsic_value_at_time REAL")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE audit_entries ADD COLUMN pe_ratio_at_time REAL")
            except Exception:
                pass
            conn.commit()
    
    def save_entry(self, entry: AuditEntry) -> AuditEntry:
        """
        Save an audit entry with its changes.
        
        Args:
            entry: AuditEntry to save
            
        Returns:
            Saved entry with assigned ID
        """
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert entry
            cursor.execute("""
                INSERT INTO audit_entries (symbol, timestamp, note, is_initial, price_at_time, intrinsic_value_at_time, pe_ratio_at_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.symbol,
                entry.timestamp.isoformat(),
                entry.note,
                1 if entry.is_initial else 0,
                entry.price_at_time,
                entry.intrinsic_value_at_time,
                entry.pe_ratio_at_time,
            ))
            
            entry_id = cursor.lastrowid
            
            # Insert changes
            for change in entry.changes:
                cursor.execute("""
                    INSERT INTO audit_changes (entry_id, field, old_value, new_value)
                    VALUES (?, ?, ?, ?)
                """, (
                    entry_id,
                    change.field.value,
                    change.old_value,
                    change.new_value,
                ))
            
            conn.commit()
            
            # Return entry with ID
            return AuditEntry(
                id=entry_id,
                symbol=entry.symbol,
                timestamp=entry.timestamp,
                changes=entry.changes,
                note=entry.note,
                is_initial=entry.is_initial,
                price_at_time=entry.price_at_time,
                intrinsic_value_at_time=entry.intrinsic_value_at_time,
                pe_ratio_at_time=entry.pe_ratio_at_time,
            )
    
    def get_history(self, symbol: str, limit: int = 50) -> List[AuditEntry]:
        """
        Get audit history for a symbol, most recent first.
        
        Args:
            symbol: Stock symbol
            limit: Maximum entries to return
            
        Returns:
            List of AuditEntry in reverse chronological order
        """
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get entries
            cursor.execute("""
                SELECT id, symbol, timestamp, note, is_initial, price_at_time, intrinsic_value_at_time, pe_ratio_at_time
                FROM audit_entries
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol.upper(), limit))
            
            entries = []
            for row in cursor.fetchall():
                # Get changes for this entry
                cursor.execute("""
                    SELECT field, old_value, new_value
                    FROM audit_changes
                    WHERE entry_id = ?
                """, (row["id"],))
                
                changes = [
                    AssumptionChange(
                        field=AssumptionField(change_row["field"]),
                        old_value=change_row["old_value"],
                        new_value=change_row["new_value"],
                    )
                    for change_row in cursor.fetchall()
                ]
                
                entries.append(AuditEntry(
                    id=row["id"],
                    symbol=row["symbol"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    changes=changes,
                    note=row["note"],
                    is_initial=bool(row["is_initial"]),
                    price_at_time=row["price_at_time"],
                    intrinsic_value_at_time=row["intrinsic_value_at_time"],
                    pe_ratio_at_time=row["pe_ratio_at_time"],
                ))
            
            return entries
    
    def get_latest_snapshot(self, symbol: str) -> Optional[AssumptionSnapshot]:
        """
        Reconstruct the current state of assumptions from history.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            AssumptionSnapshot with current values, or None if no history
        """
        history = self.get_history(symbol)
        
        if not history:
            return None
        
        # Start with empty snapshot
        snapshot = AssumptionSnapshot(symbol=symbol.upper())
        
        # Apply changes in chronological order (oldest first)
        for entry in reversed(history):
            snapshot = snapshot.apply_changes(entry.changes)
        
        return snapshot
    
    def get_field_history(
        self, 
        symbol: str, 
        field: AssumptionField,
    ) -> List[AssumptionChange]:
        """
        Get history of changes for a specific field.
        
        Args:
            symbol: Stock symbol
            field: Field to get history for
            
        Returns:
            List of changes for that field, most recent first
        """
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.field, c.old_value, c.new_value, e.timestamp
                FROM audit_changes c
                JOIN audit_entries e ON c.entry_id = e.id
                WHERE e.symbol = ? AND c.field = ?
                ORDER BY e.timestamp DESC
            """, (symbol.upper(), field.value))
            
            return [
                AssumptionChange(
                    field=AssumptionField(row["field"]),
                    old_value=row["old_value"],
                    new_value=row["new_value"],
                )
                for row in cursor.fetchall()
            ]
    
    def has_history(self, symbol: str) -> bool:
        """
        Check if a symbol has any audit history.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if history exists
        """
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM audit_entries
                WHERE symbol = ?
            """, (symbol.upper(),))
            
            return cursor.fetchone()["count"] > 0


# Singleton instance for app-wide use
_audit_repo: Optional[AuditRepository] = None


def get_audit_repository() -> AuditRepository:
    """Get the singleton audit repository instance."""
    global _audit_repo
    if _audit_repo is None:
        _audit_repo = AuditRepository()
    return _audit_repo
