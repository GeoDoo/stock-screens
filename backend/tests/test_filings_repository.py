import pytest
import zlib
from datetime import date
from app.services.filings_repository import FilingsRepository

@pytest.fixture
def repo(tmp_path):
    # Use a temporary database file
    db_path = tmp_path / "test_filings.db"
    return FilingsRepository(db_path=str(db_path))

@pytest.mark.asyncio
async def test_save_pdf_with_compression(repo):
    """Test that PDFs are compressed and size metadata is correct (P0 Bug Fix)."""
    # Create large-ish dummy data that compresses well
    original_data = b"Some financial data " * 1000
    original_size_kb = len(original_data) // 1024
    
    # Save to repo
    filing = await repo.save_pdf(
        ticker="AAPL",
        cik="0000320193",
        accession_number="0000320193-23-000106",
        form_type="10-K",
        filing_date=date(2023, 9, 30),
        document_name="aapl-20230930.htm",
        pdf_data=original_data
    )
    
    # Retrieve from repo
    retrieved_data = await repo.get_pdf("0000320193", "0000320193-23-000106", "aapl-20230930.htm")
    assert retrieved_data == original_data
    
    # Verify metadata size reflects compressed footprint
    compressed_data = zlib.compress(original_data, level=9)
    expected_compressed_kb = len(compressed_data) // 1024
    
    # Check the returned object consistency
    assert filing.uncompressed_size_kb == original_size_kb
    assert filing.compressed_size_kb == expected_compressed_kb
    assert len(filing.pdf_data) // 1024 == filing.uncompressed_size_kb

    # Check the database record directly
    from app.services.database import get_async_connection
    async with get_async_connection(repo.db_path) as db:
        async with db.execute("SELECT pdf_size_kb, original_size_kb FROM filing_pdfs LIMIT 1") as cursor:
            row = await cursor.fetchone()
            assert row["pdf_size_kb"] == expected_compressed_kb
            assert row["original_size_kb"] == original_size_kb
            # Ensure it's smaller than original
            assert row["pdf_size_kb"] < row["original_size_kb"]

@pytest.mark.asyncio
async def test_get_pdf_legacy_fallback(repo):
    """Test that uncompressed legacy data is handled correctly."""
    original_data = b"Legacy uncompressed data"
    
    # Insert uncompressed data manually into the DB
    from app.services.database import get_async_connection
    async with get_async_connection(repo.db_path) as db:
        await db.execute(
            """
            INSERT INTO filing_pdfs (
                ticker, cik, accession_number, form_type, filing_date,
                document_name, pdf_data, pdf_size_kb, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("TEST", "123", "ACC", "10-K", "2023-01-01", "doc.htm", original_data, len(original_data)//1024, "2023-01-01")
        )
        await db.commit()
    
    # Should fallback to original data if decompression fails
    retrieved = await repo.get_pdf("123", "ACC", "doc.htm")
    assert retrieved == original_data
