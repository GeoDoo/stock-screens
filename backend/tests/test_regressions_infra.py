import pytest
import asyncio
import inspect
from app.services.filings_repository import FilingsRepository
from app.services.filing_analyzer import FilingAnalyzer
from app.services.database import get_async_connection

@pytest.mark.asyncio
async def test_regression_filings_repo_auto_initializes(tmp_path):
    """
    Regression Test for Bug 1: 
    Ensures FilingsRepository creates tables automatically on __init__.
    """
    db_path = tmp_path / "regression_test.db"
    # Instantiate without manual _init_db call
    repo = FilingsRepository(db_path=str(db_path))
    
    # Attempt an operation - should not raise "no such table"
    async with get_async_connection(str(db_path)) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='filing_pdfs'") as cursor:
            row = await cursor.fetchone()
            assert row is not None, "Table 'filing_pdfs' was not created automatically"

def test_regression_gemini_analyzer_is_properly_async():
    """
    Regression Test for Bug 2: 
    Ensures FilingAnalyzer methods are coroutines and use the aio client.
    """
    analyzer = FilingAnalyzer(api_key="test_key")
    
    # 1. Verify methods are coroutines (awaitable)
    assert inspect.iscoroutinefunction(analyzer.analyze), "analyze() must be async"
    assert inspect.iscoroutinefunction(analyzer.extract_red_flags), "extract_red_flags() must be async"
    
    # 2. Verify it uses the aio (async) client path
    # We can't easily check the internal call without deep mocking, 
    # but ensuring it's a coroutine function is the first step.

@pytest.mark.asyncio
async def test_regression_filings_metadata_consistency(tmp_path):
    """
    Regression Test for Bug 1 (Metadata):
    Ensures uncompressed_size_kb matches actual data, not compressed data.
    """
    db_path = tmp_path / "metadata_regression.db"
    repo = FilingsRepository(db_path=str(db_path))
    
    test_data = b"Some data" * 100 # ~900 bytes
    original_kb = len(test_data) // 1024 # will be 0 for this small size, let's use bigger
    
    large_data = b"Large data" * 1024 # ~10KB
    large_original_kb = len(large_data) // 1024
    
    filing = await repo.save_pdf(
        ticker="TEST", cik="123", accession_number="ACC", 
        form_type="10-K", filing_date=pytest.importorskip("datetime").date(2023,1,1),
        document_name="doc.htm", pdf_data=large_data
    )
    
    assert filing.uncompressed_size_kb == large_original_kb, "Metadata uncompressed_size_kb mismatch"
    assert filing.compressed_size_kb < filing.uncompressed_size_kb or len(large_data) < 1024, "Compression should ideally reduce size"
