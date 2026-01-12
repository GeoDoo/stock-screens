import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date
from app.services.sec_filings import SECFilingsService
from app.services.filings_repository import FilingsRepository

@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test_crawler.db"
    return FilingsRepository(db_path=str(db_path))

@pytest.mark.asyncio
async def test_crawl_ticker_history(repo):
    """
    Test that crawl_ticker_history fetches all archives and persists them.
    """
    service = SECFilingsService()
    
    # 1. Setup mock responses for main submissions file and one archive file
    mock_main_json = {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "accessionNumber": ["ACC-RECENT"],
                "form": ["10-K"],
                "filingDate": ["2023-09-30"],
                "primaryDocument": ["doc1.htm"],
                "primaryDocDescription": ["Recent 10-K"]
            },
            "files": [
                {"name": "CIK0000320193-submissions-001.json"}
            ]
        }
    }
    
    mock_archive_json = {
        "accessionNumber": ["ACC-OLD"],
        "form": ["10-K"],
        "filingDate": ["2013-09-30"],
        "primaryDocument": ["doc2.htm"],
        "primaryDocDescription": ["Old 10-K"]
    }
    
    async def mocked_request(url, **kwargs):
        mock_resp = MagicMock()
        if "submissions-001" in url:
            mock_resp.json.return_value = mock_archive_json
        else:
            mock_resp.json.return_value = mock_main_json
        return mock_resp

    # 2. Patch and run crawler
    with patch.object(service, "_request", side_effect=mocked_request), \
         patch("app.services.sec_filings.get_filings_repository", return_value=repo), \
         patch.object(service, "_get_cik", AsyncMock(return_value="0000320193")):
        
        # New method: crawl_ticker_history
        stats = await service.crawl_ticker_history("AAPL")
        
        assert stats["total_found"] == 2
        assert stats["ticker"] == "AAPL"
        
        # 3. Verify both are in the DB
        persisted = await repo.list_metadata(ticker="AAPL")
        assert len(persisted) == 2
        accessions = [f["accession_number"] for f in persisted]
        assert "ACC-RECENT" in accessions
        assert "ACC-OLD" in accessions
