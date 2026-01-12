import pytest
from datetime import date
from app.services.filings_repository import FilingsRepository

@pytest.fixture
def repo(tmp_path):
    # Use a temporary database file
    db_path = tmp_path / "test_metadata.db"
    return FilingsRepository(db_path=str(db_path))

@pytest.mark.asyncio
async def test_save_and_retrieve_filing_metadata(repo):
    """
    Test that filing metadata (submissions) can be persisted and retrieved.
    """
    # 1. Define metadata
    ticker = "AAPL"
    cik = "0000320193"
    accession = "0000320193-23-000106"
    form_type = "10-K"
    filing_date = date(2023, 9, 30)
    
    # 2. Save metadata
    # We'll need a new method: save_filing_metadata
    await repo.save_metadata(
        ticker=ticker,
        cik=cik,
        accession_number=accession,
        form_type=form_type,
        filing_date=filing_date,
        description="Annual Report",
        document_name="aapl-20230930.htm"
    )
    
    # 3. Retrieve metadata
    # We'll need a new method: get_filings (filtered by ticker)
    filings = await repo.list_metadata(ticker=ticker)
    
    assert len(filings) == 1
    assert filings[0]["ticker"] == ticker
    assert filings[0]["accession_number"] == accession
    assert filings[0]["form_type"] == form_type
    assert filings[0]["filing_date"] == filing_date.isoformat()

@pytest.mark.asyncio
async def test_duplicate_metadata_replacement(repo):
    """Ensures metadata is updated/replaced if accession number already exists."""
    ticker = "AAPL"
    cik = "0000320193"
    accession = "DUPE-123"
    
    await repo.save_metadata(
        ticker=ticker, cik=cik, accession_number=accession,
        form_type="10-K", filing_date=date(2023, 1, 1),
        description="Old Description"
    )
    
    await repo.save_metadata(
        ticker=ticker, cik=cik, accession_number=accession,
        form_type="10-K", filing_date=date(2023, 1, 1),
        description="New Description"
    )
    
    filings = await repo.list_metadata(ticker=ticker)
    assert len(filings) == 1
    assert filings[0]["description"] == "New Description"
