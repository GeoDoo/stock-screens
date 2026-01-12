from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.services.database import get_async_connection, get_connection, DEFAULT_DB_PATH
from app.services.logging_config import logger # Use structlog logger

class TelemetryRepository:
    """
    Asynchronous repository for recording system telemetry.
    Tracks latency, token usage, and error rates for forensic analysis.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._init_db()

    def _init_db(self):
        """Synchronous init for startup schema safety."""
        logger.info("db_init_start", repository="TelemetryRepository", path=self.db_path)
        with get_connection(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    ticker TEXT,
                    duration_ms REAL NOT NULL,
                    tokens_used INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_trace ON telemetry(trace_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_ticker ON telemetry(ticker)")
            conn.commit()

    async def record_metric(
        self,
        trace_id: str,
        operation: str,
        duration_ms: float,
        ticker: Optional[str] = None,
        tokens_used: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """Persist a telemetry metric asynchronously."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        async with get_async_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO telemetry (
                    trace_id, operation, ticker, duration_ms, 
                    tokens_used, status, error_message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trace_id, operation, ticker, duration_ms, 
                 tokens_used, status, error_message, timestamp)
            )
            await db.commit()

# Singleton instance
_telemetry_repo: Optional[TelemetryRepository] = None

def get_telemetry_repository() -> TelemetryRepository:
    global _telemetry_repo
    if _telemetry_repo is None:
        _telemetry_repo = TelemetryRepository()
    return _telemetry_repo
