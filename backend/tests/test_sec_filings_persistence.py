import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date
from app.services.sec_filings import SECFilingsService, Filing
from app.services.filings_repository import FilingsRepository

@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test_persistence.db"
    return FilingsRepository(db_path=str(db_path))

@pytest.mark.asyncio
async def test_get_filings_persists_metadata(repo):
    """
    Test that SECFilingsService.get_filings saves fetched metadata to the repository.
    """
    # 1. Setup service with mocked repository
    service = SECFilingsService()
    
    # Mock filings data from SEC
    mock_json = {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-23-000106"],
                "form": ["10-K"],
                "filingDate": ["2023-09-30"],
                "primaryDocument": ["aapl-20230930.htm"],
                "primaryDocDescription": ["Annual Report"]
            },
            "files": []
        }
    }
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_json
    
    # Patch _request and get_filings_repository
    with patch.object(service, "_request", AsyncMock(return_value=mock_response)), \
         patch("app.services.sec_filings.get_filings_repository", return_value=repo), \
         patch.object(service, "_get_cik", AsyncMock(return_value="0000320193")):
        
        # 2. Call get_filings
        filings = await service.get_filings("AAPL")
        
        # 3. Verify it's in the DB
        persisted = await repo.list_metadata(ticker="AAPL")
        assert len(persisted) == 1
        assert persisted[0]["accession_number"] == "0000320193-23-000106"
