"""
Shared database module for all SQLite persistence.

Single database file: stock_screens.db
Tables:
- api_calls: Rate limiting call records
- api_limited: Rate limiting status flags
- audit_entries: Assumption audit trail entries
- audit_changes: Individual field changes per audit entry
- memos: Investment memos with thesis and assumptions
- memo_scenarios: Scenarios at memo creation time
- memo_market_snapshots: Periodic market tracking
- memo_post_mortems: Post-mortem reviews
- filing_pdfs: Cached SEC filing PDFs (HTML-to-PDF conversions)

Usage:
    from app.services.database import get_connection, DEFAULT_DB_PATH
    
    with get_connection() as conn:
        conn.execute("SELECT * FROM api_calls")
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


# Single database file for all persistence
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "stock_screens.db"


def get_db_path() -> str:
    """Get the default database path as string."""
    return str(DEFAULT_DB_PATH)


@contextmanager
def get_connection(db_path: Optional[str] = None):
    """
    Get a database connection with proper cleanup.
    
    Args:
        db_path: Optional path override. Defaults to stock_screens.db
        
    Yields:
        sqlite3.Connection with Row factory enabled
    """
    path = db_path or str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
