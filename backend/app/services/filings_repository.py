"""
Filings Repository - SQLite persistence for SEC filing PDFs.

Caches generated PDFs to avoid repeated expensive HTML-to-PDF conversions.
"""
import logging
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Optional

from app.services.database import get_async_connection, get_connection, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


@dataclass
class CachedFiling:
    """A cached SEC filing PDF."""
    
    id: int
    ticker: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: date
    document_name: str
    pdf_data: bytes
    compressed_size_kb: int    # Database footprint (compressed)
    uncompressed_size_kb: int  # Actual PDF size (uncompressed)
    created_at: datetime
    
    @property
    def document_url(self) -> str:
        """Reconstruct the SEC document URL."""
        cik_num = self.cik.lstrip("0")
        accession_clean = self.accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession_clean}/{self.document_name}"


class FilingsRepository:
    """
    Asynchronous SQLite-based repository for caching SEC filing PDFs.
    
    Tables:
    - filing_pdfs: Cached PDF data with metadata
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize repository with database path."""
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        # Note: _init_db() should be called externally or handled via an async init
        # to avoid blocking the event loop in the constructor.
    
    async def _init_db(self):
        """Initialize database schema (Async)."""
        async with get_async_connection(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS filing_pdfs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    cik TEXT NOT NULL,
                    accession_number TEXT NOT NULL,
                    form_type TEXT NOT NULL,
                    filing_date TEXT NOT NULL,
                    document_name TEXT NOT NULL,
                    pdf_data BLOB NOT NULL,
                    pdf_size_kb INTEGER NOT NULL,
                    original_size_kb INTEGER,
                    created_at TEXT NOT NULL,
                    
                    -- Unique constraint: one PDF per document
                    UNIQUE(cik, accession_number, document_name)
                );
                
                CREATE INDEX IF NOT EXISTS idx_filing_pdfs_ticker 
                    ON filing_pdfs(ticker);
                CREATE INDEX IF NOT EXISTS idx_filing_pdfs_cik 
                    ON filing_pdfs(cik);
                CREATE INDEX IF NOT EXISTS idx_filing_pdfs_accession 
                    ON filing_pdfs(accession_number);
                CREATE INDEX IF NOT EXISTS idx_filing_pdfs_form_type 
                    ON filing_pdfs(form_type);
                CREATE INDEX IF NOT EXISTS idx_filing_pdfs_filing_date 
                    ON filing_pdfs(filing_date DESC);
            """)
            
            # Migration: add original_size_kb if it doesn't exist
            async with db.execute("PRAGMA table_info(filing_pdfs)") as cursor:
                columns = [row["name"] for row in await cursor.fetchall()]
                if "original_size_kb" not in columns:
                    await db.execute("ALTER TABLE filing_pdfs ADD COLUMN original_size_kb INTEGER")
            
            await db.commit()
    
    async def get_pdf(
        self,
        cik: str,
        accession_number: str,
        document_name: str,
    ) -> Optional[bytes]:
        """
        Get a cached PDF by its unique identifier (Async).
        
        Returns:
            PDF bytes if cached, None otherwise.
        """
        async with get_async_connection(self.db_path) as db:
            async with db.execute(
                """
                SELECT pdf_data FROM filing_pdfs
                WHERE cik = ? AND accession_number = ? AND document_name = ?
                """,
                (cik, accession_number, document_name),
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    logger.info(
                        f"Cache hit for {document_name} (CIK: {cik}, "
                        f"Accession: {accession_number})"
                    )
                    try:
                        # Decompress data on retrieval
                        return zlib.decompress(row["pdf_data"])
                    except zlib.error:
                        # Fallback for uncompressed legacy data
                        return row["pdf_data"]
                
                return None
    
    async def save_pdf(
        self,
        ticker: str,
        cik: str,
        accession_number: str,
        form_type: str,
        filing_date: date,
        document_name: str,
        pdf_data: bytes,
    ) -> CachedFiling:
        """
        Save a PDF to the cache with Zlib compression (Async).
        
        If the PDF already exists, it will be replaced.
        """
        # Compress data before saving
        compressed_data = zlib.compress(pdf_data, level=9)
        original_size_kb = len(pdf_data) // 1024
        compressed_size_kb = len(compressed_data) // 1024
        
        created_at = datetime.now(timezone.utc)
        
        async with get_async_connection(self.db_path) as db:
            async with db.execute(
                """
                INSERT OR REPLACE INTO filing_pdfs (
                    ticker, cik, accession_number, form_type, filing_date,
                    document_name, pdf_data, pdf_size_kb, original_size_kb, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker.upper(),
                    cik,
                    accession_number,
                    form_type,
                    filing_date.isoformat(),
                    document_name,
                    compressed_data,
                    compressed_size_kb,
                    original_size_kb,
                    created_at.isoformat(),
                ),
            ) as cursor:
                await db.commit()
                filing_id = cursor.lastrowid
            
            logger.info(
                f"Cached PDF for {ticker} {form_type} ({document_name}): "
                f"{original_size_kb} KB -> {compressed_size_kb} KB "
                f"({round((1 - compressed_size_kb/original_size_kb)*100, 1) if original_size_kb > 0 else 0}% saving)"
            )
            
            return CachedFiling(
                id=filing_id,
                ticker=ticker.upper(),
                cik=cik,
                accession_number=accession_number,
                form_type=form_type,
                filing_date=filing_date,
                document_name=document_name,
                pdf_data=pdf_data,
                compressed_size_kb=compressed_size_kb,
                uncompressed_size_kb=original_size_kb,
                created_at=created_at,
            )
    
    async def list_cached(
        self,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[CachedFiling]:
        """List cached filings with optional filtering (without PDF data) (Async)."""
        async with get_async_connection(self.db_path) as db:
            query = """
                SELECT id, ticker, cik, accession_number, form_type, 
                       filing_date, document_name, pdf_size_kb as compressed_size_kb, 
                       original_size_kb as uncompressed_size_kb, created_at
                FROM filing_pdfs
                WHERE 1=1
            """
            params = []
            
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker.upper())
            
            if form_type:
                query += " AND form_type = ?"
                params.append(form_type)
            
            query += " ORDER BY filing_date DESC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    CachedFiling(
                        id=row["id"],
                        ticker=row["ticker"],
                        cik=row["cik"],
                        accession_number=row["accession_number"],
                        form_type=row["form_type"],
                        filing_date=date.fromisoformat(row["filing_date"]),
                        document_name=row["document_name"],
                        pdf_data=b"",  # Don't load blob in list view
                        compressed_size_kb=row["compressed_size_kb"],
                        uncompressed_size_kb=row["uncompressed_size_kb"] or 0,
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                    for row in rows
                ]
    
    async def delete_pdf(
        self,
        cik: str,
        accession_number: str,
        document_name: str,
    ) -> bool:
        """Delete a cached PDF. Returns True if deleted, False if not found (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute(
                """
                DELETE FROM filing_pdfs
                WHERE cik = ? AND accession_number = ? AND document_name = ?
                """,
                (cik, accession_number, document_name),
            ) as cursor:
                await db.commit()
                return cursor.rowcount > 0
    
    async def get_cache_stats(self) -> dict:
        """Get cache statistics (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(pdf_size_kb) as total_compressed_kb,
                    SUM(original_size_kb) as total_uncompressed_kb,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    COUNT(DISTINCT form_type) as unique_form_types
                FROM filing_pdfs
            """) as cursor:
                row = await cursor.fetchone()
                
                compressed_kb = row["total_compressed_kb"] or 0
                uncompressed_kb = row["total_uncompressed_kb"] or 0
                
                return {
                    "total_files": row["total_files"] or 0,
                    "total_size_mb": round(compressed_kb / 1024, 2),
                    "original_size_mb": round(uncompressed_kb / 1024, 2),
                    "savings_percent": round((1 - compressed_kb / uncompressed_kb) * 100, 1) if uncompressed_kb > 0 else 0,
                    "unique_tickers": row["unique_tickers"] or 0,
                    "unique_form_types": row["unique_form_types"] or 0,
                }
    
    async def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear cached PDFs (Async).
        
        Args:
            older_than_days: If provided, only clear PDFs older than N days.
                           If None, clears all PDFs.
        
        Returns:
            Number of PDFs deleted.
        """
        async with get_async_connection(self.db_path) as db:
            if older_than_days is not None:
                async with db.execute(
                    """
                    DELETE FROM filing_pdfs
                    WHERE datetime(created_at) < datetime('now', ?)
                    """,
                    (f"-{older_than_days} days",),
                ) as cursor:
                    await db.commit()
                    deleted = cursor.rowcount
            else:
                async with db.execute("DELETE FROM filing_pdfs") as cursor:
                    await db.commit()
                    deleted = cursor.rowcount
            
            logger.info(f"Cleared {deleted} cached PDFs")
            return deleted


# Singleton instance
_filings_repo: Optional[FilingsRepository] = None


def get_filings_repository() -> FilingsRepository:
    """Get the singleton filings repository instance."""
    global _filings_repo
    if _filings_repo is None:
        _filings_repo = FilingsRepository()
    return _filings_repo
