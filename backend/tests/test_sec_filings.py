"""Tests for SEC filings service."""
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.sec_filings import (
    SECFilingsService,
    SECFilingsError,
    Filing,
    sec_filings_service,
)


class TestFilingDataclass:
    """Test Filing dataclass."""

    def test_filing_creation(self):
        filing = Filing(
            accession_number="0000320193-25-000079",
            form_type="10-K",
            filing_date=date(2025, 10, 31),
            description="Annual Report",
            document_url="https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm",
            document_name="aapl-20250927.htm",
            cik="0000320193",
            ticker="AAPL",
        )
        assert filing.form_type == "10-K"
        assert filing.ticker == "AAPL"
        assert filing.document_name == "aapl-20250927.htm"
    
    def test_viewer_url(self):
        filing = Filing(
            accession_number="0000320193-25-000079",
            form_type="10-K",
            filing_date=date(2025, 10, 31),
            description="Annual Report",
            document_url="https://example.com",
            document_name="aapl-20250927.htm",
            cik="0000320193",
            ticker="AAPL",
        )
        # Should link to filing index page
        assert "320193" in filing.viewer_url
        assert "000032019325000079" in filing.viewer_url
        assert "-index.htm" in filing.viewer_url


class TestSECFilingsService:
    """Test SEC filings service."""

    @pytest.fixture
    def service(self):
        return SECFilingsService()
    
    @pytest.mark.asyncio
    async def test_get_cik_from_ticker(self, service):
        """Test ticker to CIK mapping."""
        mock_ticker_map = {
            "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}
        }
        
        with patch.object(service, '_request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_ticker_map
            mock_request.return_value = mock_response
            
            cik = await service._get_cik("AAPL")
            assert cik == "0000320193"
    
    @pytest.mark.asyncio
    async def test_get_cik_not_found(self, service):
        """Test ticker not found raises error."""
        mock_ticker_map = {}
        
        with patch.object(service, '_request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_ticker_map
            mock_request.return_value = mock_response
            
            with pytest.raises(SECFilingsError, match="not found"):
                await service._get_cik("INVALID")
    
    @pytest.mark.asyncio
    async def test_get_filings_returns_list(self, service):
        """Test get_filings returns list of Filing objects."""
        mock_ticker_map = {
            "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_submissions = {
            "cik": "320193",
            "name": "Apple Inc.",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-25-000079", "0000320193-25-000050"],
                    "form": ["10-K", "10-Q"],
                    "filingDate": ["2025-10-31", "2025-08-01"],
                    "primaryDocument": ["aapl-20250927.htm", "aapl-20250629.htm"],
                    "primaryDocDescription": ["10-K", "10-Q"],
                }
            }
        }
        
        with patch.object(service, '_request', new_callable=AsyncMock) as mock_request:
            mock_response1 = MagicMock()
            mock_response1.json.return_value = mock_ticker_map
            mock_response2 = MagicMock()
            mock_response2.json.return_value = mock_submissions
            mock_request.side_effect = [mock_response1, mock_response2]
            
            filings = await service.get_filings("AAPL", limit=5)
            
            assert len(filings) == 2
            assert filings[0].form_type == "10-K"
            assert filings[1].form_type == "10-Q"
            assert all(isinstance(f, Filing) for f in filings)
    
    @pytest.mark.asyncio
    async def test_get_filings_with_form_filter(self, service):
        """Test filtering by form type."""
        mock_ticker_map = {
            "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_submissions = {
            "cik": "320193",
            "name": "Apple Inc.",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-25-000079", "0000320193-25-000050", "0000320193-25-000030"],
                    "form": ["10-K", "10-Q", "8-K"],
                    "filingDate": ["2025-10-31", "2025-08-01", "2025-06-01"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm"],
                    "primaryDocDescription": ["10-K", "10-Q", "8-K"],
                }
            }
        }
        
        with patch.object(service, '_request', new_callable=AsyncMock) as mock_request:
            mock_response1 = MagicMock()
            mock_response1.json.return_value = mock_ticker_map
            mock_response2 = MagicMock()
            mock_response2.json.return_value = mock_submissions
            mock_request.side_effect = [mock_response1, mock_response2]
            
            filings = await service.get_filings("AAPL", form_types=["10-K"], limit=5)
            
            assert len(filings) == 1
            assert filings[0].form_type == "10-K"
    
    def test_build_document_url(self, service):
        """Test document URL construction."""
        url = service._build_document_url(
            cik="0000320193",
            accession="0000320193-25-000079",
            document="aapl-20250927.htm"
        )
        assert url == "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"


class TestFilingsRouter:
    """Test filings API router."""
    
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_get_filings_endpoint(self, client):
        """Test /api/filings/{ticker} endpoint."""
        mock_filings = [
            Filing(
                accession_number="0000320193-25-000079",
                form_type="10-K",
                filing_date=date(2025, 10, 31),
                description="10-K",
                document_url="https://example.com/doc.htm",
                document_name="doc.htm",
                cik="0000320193",
                ticker="AAPL",
            )
        ]
        mock_company_info = {
            "cik": "0000320193",
            "name": "Apple Inc.",
            "ticker": "AAPL",
        }
        
        with patch("app.routers.filings.sec_filings_service.get_filings", new_callable=AsyncMock) as mock_get:
            with patch("app.routers.filings.sec_filings_service.get_company_info", new_callable=AsyncMock) as mock_info:
                mock_get.return_value = mock_filings
                mock_info.return_value = mock_company_info
                
                response = client.get("/api/filings/AAPL")
                
                assert response.status_code == 200
                data = response.json()
                assert data["ticker"] == "AAPL"
                assert data["company_name"] == "Apple Inc."
                assert len(data["filings"]) == 1
                assert data["filings"][0]["form_type"] == "10-K"
    
    def test_get_filings_not_found(self, client):
        """Test 404 for invalid ticker."""
        with patch("app.routers.filings.sec_filings_service.get_filings", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = SECFilingsError("Ticker 'INVALID' not found")
            
            response = client.get("/api/filings/INVALID")
            
            assert response.status_code == 404
    
    def test_get_company_info_endpoint(self, client):
        """Test /api/filings/{ticker}/info endpoint."""
        mock_info = {
            "cik": "0000320193",
            "name": "Apple Inc.",
            "ticker": "AAPL",
            "sic": "3571",
            "sic_description": "Electronic Computers",
        }
        
        with patch("app.routers.filings.sec_filings_service.get_company_info", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_info
            
            response = client.get("/api/filings/AAPL/info")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Apple Inc."
            assert data["cik"] == "0000320193"
