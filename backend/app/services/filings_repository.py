"""
Filings Repository - SQLite persistence for SEC filing PDFs.

Caches generated PDFs to avoid repeated expensive HTML-to-PDF conversions.
"""
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Optional

from app.services.database import get_async_connection, get_connection, DEFAULT_DB_PATH
from app.services.logging_config import logger # Use structlog logger


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
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema (Synchronous for startup)."""
        with get_connection(self.db_path) as conn:
            conn.executescript("""
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

                CREATE TABLE IF NOT EXISTS sec_filings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    cik TEXT NOT NULL,
                    accession_number TEXT NOT NULL,
                    form_type TEXT NOT NULL,
                    filing_date TEXT NOT NULL,
                    description TEXT,
                    document_name TEXT,
                    sentiment_score REAL,
                    consistency_score INTEGER,
                    forensic_report_json TEXT,
                    parsed_status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    
                    -- Unique constraint: one entry per accession number
                    UNIQUE(accession_number)
                );
                
                CREATE INDEX IF NOT EXISTS idx_sec_filings_ticker 
                    ON sec_filings(ticker);
                CREATE INDEX IF NOT EXISTS idx_sec_filings_date 
                    ON sec_filings(filing_date DESC);

                CREATE TABLE IF NOT EXISTS filing_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accession_number TEXT NOT NULL,
                    section_name TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    content_hash TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(accession_number) REFERENCES sec_filings(accession_number),
                    UNIQUE(accession_number, section_name)
                );
                
                CREATE INDEX IF NOT EXISTS idx_filing_sections_accession 
                    ON filing_sections(accession_number);
            """)
            
            # Migration: add original_size_kb if it doesn't exist
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(filing_pdfs)")
            columns = [row[1] for row in cursor.fetchall()]
            if "original_size_kb" not in columns:
                conn.execute("ALTER TABLE filing_pdfs ADD COLUMN original_size_kb INTEGER")
            
            # Migration: add forensic columns to sec_filings
            cursor.execute("PRAGMA table_info(sec_filings)")
            sec_columns = [row[1] for row in cursor.fetchall()]
            if "consistency_score" not in sec_columns:
                conn.execute("ALTER TABLE sec_filings ADD COLUMN consistency_score INTEGER")
            if "forensic_report_json" not in sec_columns:
                conn.execute("ALTER TABLE sec_filings ADD COLUMN forensic_report_json TEXT")
            
            conn.commit()
    
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
                        "cache_hit",
                        document_name=document_name,
                        cik=cik,
                        accession_number=accession_number
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
                "pdf_cached",
                ticker=ticker,
                form_type=form_type,
                document_name=document_name,
                original_size_kb=original_size_kb,
                compressed_size_kb=compressed_size_kb,
                savings_percent=round((1 - compressed_size_kb/original_size_kb)*100, 1) if original_size_kb > 0 else 0
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
            
            logger.info("cache_cleared", count=deleted)
            return deleted

    async def save_metadata(
        self,
        ticker: str,
        cik: str,
        accession_number: str,
        form_type: str,
        filing_date: date,
        description: Optional[str] = None,
        document_name: Optional[str] = None,
    ):
        """Save SEC filing metadata to the database (Async)."""
        created_at = datetime.now(timezone.utc).isoformat()
        
        async with get_async_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO sec_filings (
                    ticker, cik, accession_number, form_type, 
                    filing_date, description, document_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker.upper(),
                    cik,
                    accession_number,
                    form_type,
                    filing_date.isoformat(),
                    description,
                    document_name,
                    created_at
                )
            )
            await db.commit()

    async def list_metadata(
        self,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """List filing metadata from the database (Async)."""
        async with get_async_connection(self.db_path) as db:
            query = "SELECT * FROM sec_filings WHERE 1=1"
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
                return [dict(row) for row in rows]

    async def update_forensic_report(
        self,
        accession_number: str,
        consistency_score: int,
        report_json: str,
    ):
        """Update a filing with its forensic analysis results (Async)."""
        async with get_async_connection(self.db_path) as db:
            await db.execute(
                """
                UPDATE sec_filings 
                SET consistency_score = ?, forensic_report_json = ?, parsed_status = 'completed'
                WHERE accession_number = ?
                """,
                (consistency_score, report_json, accession_number)
            )
            await db.commit()

    async def save_section(
        self,
        accession_number: str,
        section_name: str,
        content_text: str,
    ):
        """Save a granular section of a filing (Async)."""
        import hashlib
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()
        
        async with get_async_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO filing_sections (
                    accession_number, section_name, content_text, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (accession_number, section_name, content_text, content_hash, created_at)
            )
            await db.commit()

    async def get_sections(self, accession_number: str) -> list[dict]:
        """Get all sections for a specific filing (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM filing_sections WHERE accession_number = ?",
                (accession_number,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_section(self, accession_number: str, section_name: str) -> Optional[dict]:
        """Get a specific section by name (Async)."""
        async with get_async_connection(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM filing_sections WHERE accession_number = ? AND section_name = ?",
                (accession_number, section_name)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None


# Singleton instance
_filings_repo: Optional[FilingsRepository] = None


def get_filings_repository() -> FilingsRepository:
    """Get the singleton filings repository instance."""
    global _filings_repo
    if _filings_repo is None:
        _filings_repo = FilingsRepository()
    return _filings_repo
