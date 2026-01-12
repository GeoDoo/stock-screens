"""
Audit Repository - SQLite persistence for assumption audit trail.

Stores and retrieves assumption change history for investment thesis tracking.
"""
from datetime import datetime
from typing import List, Optional

from app.services.database import get_async_connection, get_connection, DEFAULT_DB_PATH
from app.models.assumption_audit import (
    AssumptionField,
    AssumptionChange,
    AuditEntry,
    AssumptionSnapshot,
)


class AuditRepository:
    """
    Asynchronous SQLite-based repository for assumption audit entries.
    
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
        """Initialize database schema if not exists (Synchronous for startup)."""
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
            # Migration: Add new columns if they don't exist
            try:
                conn.execute("ALTER TABLE audit_entries ADD COLUMN price_at_time REAL")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE audit_entries ADD COLUMN intrinsic_value_at_time REAL")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE audit_entries ADD COLUMN pe_ratio_at_time REAL")
            except Exception:
                pass
            
            self._migrate_audit_changes_allow_null_new_value(conn)
            conn.commit()
    
    def _migrate_audit_changes_allow_null_new_value(self, conn):
        """Recreate table to allow NULL if needed."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(audit_changes)")
        columns = cursor.fetchall()
        for col in columns:
            if col[1] == "new_value" and col[3] == 1:
                cursor.executescript("""
                    CREATE TABLE audit_changes_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entry_id INTEGER NOT NULL,
                        field TEXT NOT NULL,
                        old_value REAL,
                        new_value REAL,
                        FOREIGN KEY (entry_id) REFERENCES audit_entries(id)
                    );
                    INSERT INTO audit_changes_new (id, entry_id, field, old_value, new_value)
                    SELECT id, entry_id, field, old_value, new_value FROM audit_changes;
                    DROP TABLE audit_changes;
                    ALTER TABLE audit_changes_new RENAME TO audit_changes;
                    CREATE INDEX IF NOT EXISTS idx_changes_entry ON audit_changes(entry_id);
                """)
                break
    
    async def save_entry(self, entry: AuditEntry) -> AuditEntry:
        """Save an audit entry with its changes (Async)."""
        async with get_async_connection(self.db_path) as db:
            # Insert entry
            async with db.execute("""
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
            )) as cursor:
                entry_id = cursor.lastrowid
            
            # Insert changes
            for change in entry.changes:
                await db.execute("""
                    INSERT INTO audit_changes (entry_id, field, old_value, new_value)
                    VALUES (?, ?, ?, ?)
                """, (
                    entry_id,
                    change.field.value,
                    change.old_value,
                    change.new_value,
                ))
            
            await db.commit()
            
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
    
    async def get_history(self, symbol: str, limit: int = 50) -> List[AuditEntry]:
        """Get audit history for a symbol (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute("""
                SELECT id, symbol, timestamp, note, is_initial, price_at_time, intrinsic_value_at_time, pe_ratio_at_time
                FROM audit_entries
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol.upper(), limit)) as cursor:
                entries = []
                for row in await cursor.fetchall():
                    async with db.execute("""
                        SELECT field, old_value, new_value
                        FROM audit_changes
                        WHERE entry_id = ?
                    """, (row["id"],)) as change_cursor:
                        changes = [
                            AssumptionChange(
                                field=AssumptionField(change_row["field"]),
                                old_value=change_row["old_value"],
                                new_value=change_row["new_value"],
                            )
                            for change_row in await change_cursor.fetchall()
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
    
    async def get_latest_snapshot(self, symbol: str) -> Optional[AssumptionSnapshot]:
        """Reconstruct the current state of assumptions from history (Async)."""
        history = await self.get_history(symbol)
        if not history:
            return None
        snapshot = AssumptionSnapshot(symbol=symbol.upper())
        for entry in reversed(history):
            snapshot = snapshot.apply_changes(entry.changes)
        return snapshot
    
    async def get_field_history(
        self, 
        symbol: str, 
        field: AssumptionField,
    ) -> List[AssumptionChange]:
        """Get history of changes for a specific field (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute("""
                SELECT c.field, c.old_value, c.new_value, e.timestamp
                FROM audit_changes c
                JOIN audit_entries e ON c.entry_id = e.id
                WHERE e.symbol = ? AND c.field = ?
                ORDER BY e.timestamp DESC
            """, (symbol.upper(), field.value)) as cursor:
                return [
                    AssumptionChange(
                        field=AssumptionField(row["field"]),
                        old_value=row["old_value"],
                        new_value=row["new_value"],
                    )
                    for row in await cursor.fetchall()
                ]
    
    async def has_history(self, symbol: str) -> bool:
        """Check if a symbol has any audit history (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) as count
                FROM audit_entries
                WHERE symbol = ?
            """, (symbol.upper(),)) as cursor:
                row = await cursor.fetchone()
                return row["count"] > 0


# Singleton instance for app-wide use
_audit_repo: Optional[AuditRepository] = None


def get_audit_repository() -> AuditRepository:
    """Get the singleton audit repository instance."""
    global _audit_repo
    if _audit_repo is None:
        _audit_repo = AuditRepository()
    return _audit_repo
