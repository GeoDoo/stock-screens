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
        # Should link to filing folder (lists all documents)
        assert "320193" in filing.viewer_url
        assert "000032019325000079" in filing.viewer_url
        assert filing.viewer_url.endswith("/")


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

    @pytest.mark.asyncio
    async def test_get_company_info(self, service):
        """Test fetching company info from SEC."""
        mock_submissions = {
            "name": "Apple Inc.",
            "sic": "3571",
            "sicDescription": "Electronic Computers",
        }
        
        with patch.object(service, '_get_cik', new_callable=AsyncMock) as mock_get_cik:
            with patch.object(service, '_request', new_callable=AsyncMock) as mock_request:
                mock_get_cik.return_value = "0000320193"
                mock_response = MagicMock()
                mock_response.json.return_value = mock_submissions
                mock_request.return_value = mock_response
                
                info = await service.get_company_info("AAPL")
                
                assert info["name"] == "Apple Inc."
                assert info["ticker"] == "AAPL"
                assert info["cik"] == "0000320193"
                assert info["sic"] == "3571"

    @pytest.mark.asyncio
    async def test_audit_ticker_history_resilience(self, service):
        """Test audit_ticker_history skips entries with missing document_name."""
        mock_metadata = [
            {
                "accession_number": "001",
                "cik": "123",
                "document_name": None, # Should be skipped
                "parsed_status": "pending"
            },
            {
                "accession_number": "002",
                "cik": "123",
                "document_name": "doc.htm",
                "parsed_status": "pending"
            }
        ]
        
        with patch("app.services.sec_filings.get_filings_repository") as mock_repo_func:
            with patch("app.services.sec_filings.get_filing_analyzer") as mock_analyzer_func:
                mock_repo = AsyncMock()
                mock_repo.list_metadata.return_value = mock_metadata
                mock_repo_func.return_value = mock_repo
                
                mock_analyzer = AsyncMock()
                mock_analyzer_func.return_value = mock_analyzer
                
                with patch.object(service, 'get_filing_html', new_callable=AsyncMock) as mock_get_html:
                    mock_get_html.return_value = "<html></html>"
                    
                    # Also patch asyncio.sleep to avoid waiting
                    with patch("asyncio.sleep", new_callable=AsyncMock):
                        await service.audit_ticker_history("AAPL", limit=2)
                
                # Verify get_filing_html was called only once (for the second entry)
                assert mock_get_html.call_count == 1
                assert "002" in mock_get_html.call_args[0][0]
                
                # Verify update_forensic_report was called only once
                assert mock_repo.update_forensic_report.call_count == 1

    @pytest.mark.asyncio
    async def test_get_company_info(self, service):
        """Test fetching company info from SEC."""
        mock_submissions = {
            "name": "Apple Inc.",
            "sic": "3571",
            "sicDescription": "Electronic Computers",
        }
        
        with patch.object(service, '_get_cik', new_callable=AsyncMock) as mock_get_cik:
            with patch.object(service, '_request', new_callable=AsyncMock) as mock_request:
                mock_get_cik.return_value = "0000320193"
                mock_response = MagicMock()
                mock_response.json.return_value = mock_submissions
                mock_request.return_value = mock_response
                
                info = await service.get_company_info("AAPL")
                
                assert info["name"] == "Apple Inc."
                assert info["ticker"] == "AAPL"
                assert info["cik"] == "0000320193"
                assert info["sic"] == "3571"

    @pytest.mark.asyncio
    async def test_audit_ticker_history_skips_missing_doc_name(self, service):
        """Test that audit_ticker_history skips entries with NULL document_name."""
        mock_metadata = [
            {
                "accession_number": "001",
                "cik": "123",
                "document_name": None, # Should be skipped
                "parsed_status": "pending"
            },
            {
                "accession_number": "002",
                "cik": "123",
                "document_name": "doc.htm",
                "parsed_status": "pending"
            }
        ]
        
        with patch("app.services.sec_filings.get_filings_repository") as mock_repo_func:
            with patch("app.services.sec_filings.get_filing_analyzer") as mock_analyzer_func:
                mock_repo = AsyncMock()
                mock_repo.list_metadata.return_value = mock_metadata
                mock_repo_func.return_value = mock_repo
                
                mock_analyzer = AsyncMock()
                mock_analyzer_func.return_value = mock_analyzer
                
                with patch.object(service, 'get_filing_html', new_callable=AsyncMock) as mock_get_html:
                    mock_get_html.return_value = "<html></html>"
                    mock_report = MagicMock()
                    mock_report.accounting_consistency_score = 90
                    mock_report.model_dump_json.return_value = "{}"
                    mock_analyzer.analyze_forensic.return_value = mock_report
                    
                    # Also patch asyncio.sleep to avoid waiting
                    with patch("asyncio.sleep", new_callable=AsyncMock):
                        await service.audit_ticker_history("AAPL", limit=2)
                
                # Verify get_filing_html was called only once (for the second entry)
                assert mock_get_html.call_count == 1
                assert "002" in mock_get_html.call_args[0][0]
                
                # Verify update_forensic_report was called only once
                assert mock_repo.update_forensic_report.call_count == 1
                mock_repo.update_forensic_report.assert_called_with(
                    accession_number="002",
                    consistency_score=90,
                    report_json="{}"
                )


class TestFilingsRouter:
    """Test filings API router."""
    
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_get_filings_endpoint(self, client):
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
    
    @pytest.mark.asyncio
    async def test_get_filings_not_found(self, client):
        """Test 404 for invalid ticker."""
        with patch("app.routers.filings.sec_filings_service.get_filings", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = SECFilingsError("Ticker 'INVALID' not found")
            
            response = client.get("/api/filings/INVALID")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_company_info_endpoint(self, client):
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
    
    @pytest.mark.asyncio
    async def test_forensic_audit_no_external_api_calls(self, client):
        """
        SINGLE SOURCE OF TRUTH: Forensic audit must ONLY use data from the SEC filing.
        No calls to external providers (FMP, Yahoo, etc.) are allowed.
        """
        with patch("app.routers.filings.sec_filings_service.get_filing_html", new_callable=AsyncMock) as mock_html:
            with patch("app.routers.filings.get_filing_analyzer") as mock_analyzer_func:
                with patch("app.routers.filings.get_stock_client") as mock_get_client:
                    # Provide minimal HTML with iXBRL data
                    mock_html.return_value = """<html><body>
                        <ix:nonfraction name="us-gaap:Revenues" contextRef="FY2024" decimals="-6">164501000000</ix:nonfraction>
                        <ix:nonfraction name="us-gaap:NetIncomeLoss" contextRef="FY2024" decimals="-6">62360000000</ix:nonfraction>
                    </body></html>"""
                    
                    mock_analyzer = AsyncMock()
                    mock_analyzer.analyze_forensic.return_value = MagicMock(
                        accounting_consistency_score=85,
                        red_flags=[],
                        summary="Test summary",
                        reported_eps=None,
                        forensic_eps_adjustment=0.0,
                        adjustments=[],
                        model="gemini-2.5-flash",
                        model_dump_json=lambda: "{}"
                    )
                    mock_analyzer_func.return_value = mock_analyzer
                    
                    response = client.post(
                        "/api/filings/AAPL/forensic-audit?document_url=https://example.com/filing.htm"
                    )
                    
                    assert response.status_code == 200
                    
                    # CRITICAL: get_stock_client should NEVER be called
                    mock_get_client.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_forensic_audit_rate_limit_returns_valid_schema(self, client):
        """
        Regression test: When LLM hits rate limit, error handler must return
        valid ForensicReport with properly structured RedFlagCategory objects.
        
        RedFlagCategory requires:
        - category: str
        - score: int (1-10)
        - severity: str ("Low", "Medium", "High", "Critical")
        - findings: List[str]
        - evidence_quotes: List[str]
        """
        from app.services.filing_analyzer import RateLimitError
        
        with patch("app.routers.filings.sec_filings_service.get_filing_html", new_callable=AsyncMock) as mock_html:
            with patch("app.routers.filings.get_filing_analyzer") as mock_analyzer_func:
                mock_html.return_value = "<html><body>Test filing content</body></html>"
                
                mock_analyzer = AsyncMock()
                mock_analyzer.analyze_forensic.side_effect = RateLimitError(retry_after=60)
                mock_analyzer_func.return_value = mock_analyzer
                
                response = client.post(
                    "/api/filings/AAPL/forensic-audit?document_url=https://example.com/filing.htm"
                )
                
                # Should return 200 with graceful degradation, not 500
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                
                data = response.json()
                report = data["report"]
                
                # Verify model indicates rate-limited
                assert report["model"] == "rate-limited"
                
                # Verify red_flags has correct schema
                assert len(report["red_flags"]) >= 1
                red_flag = report["red_flags"][0]
                
                # These are the required fields per RedFlagCategory schema
                assert "category" in red_flag
                assert "score" in red_flag
                assert isinstance(red_flag["score"], int)
                assert 1 <= red_flag["score"] <= 10
                assert "severity" in red_flag
                assert red_flag["severity"] in ["Low", "Medium", "High", "Critical"]
                assert "findings" in red_flag
                assert isinstance(red_flag["findings"], list)
                assert "evidence_quotes" in red_flag
                assert isinstance(red_flag["evidence_quotes"], list)
    
    @pytest.mark.asyncio
    async def test_forensic_audit_generic_error_returns_valid_schema(self, client):
        """
        Regression test: When LLM throws generic exception, error handler must
        return valid ForensicReport with properly structured RedFlagCategory.
        """
        with patch("app.routers.filings.sec_filings_service.get_filing_html", new_callable=AsyncMock) as mock_html:
            with patch("app.routers.filings.get_filing_analyzer") as mock_analyzer_func:
                mock_html.return_value = "<html><body>Test filing content</body></html>"
                
                mock_analyzer = AsyncMock()
                mock_analyzer.analyze_forensic.side_effect = Exception("Unexpected LLM error")
                mock_analyzer_func.return_value = mock_analyzer
                
                response = client.post(
                    "/api/filings/AAPL/forensic-audit?document_url=https://example.com/filing.htm"
                )
                
                # Should return 200 with error report, not 500
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                
                data = response.json()
                report = data["report"]
                
                # Verify model indicates error
                assert report["model"] == "error"
                
                # Verify red_flags has correct schema
                red_flag = report["red_flags"][0]
                assert "score" in red_flag
                assert isinstance(red_flag["score"], int)
                assert "severity" in red_flag
                assert red_flag["severity"] in ["Low", "Medium", "High", "Critical"]
                assert "findings" in red_flag
                assert isinstance(red_flag["findings"], list)
