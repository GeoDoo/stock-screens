import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import date
from app.services.sec_filings import SECFilingsService, Filing, SECFilingsError
from app.services.filing_analyzer import FilingAnalyzer, AnalyzerError, RateLimitError

@pytest.fixture
def sec_service():
    return SECFilingsService(user_agent="TestAgent")

@pytest.fixture
def analyzer():
    # Mock API key for testing
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
        return FilingAnalyzer(api_key="test_key")

class TestSECFilingsService:
    @pytest.mark.asyncio
    async def test_cik_lookup_normalization(self, sec_service):
        """Test that ticker symbols are normalized correctly for CIK lookup."""
        # Reset cache to ensure load_ticker_map is called
        sec_service._cik_cache = {}
        
        with patch.object(sec_service, "_load_ticker_map") as mock_map:
            # First call for AAPL
            mock_map.return_value = {"AAPL": "0000320193"}
            cik = await sec_service._get_cik("aapl")
            assert cik == "0000320193"
            
            # Second call for BRK.B (normalized to BRK-B)
            mock_map.return_value = {"BRK-B": "0001067983"}
            cik = await sec_service._get_cik("BRK.B")
            assert cik == "0001067983"

    def test_document_url_builder(self, sec_service):
        """Test SEC document URL construction."""
        url = sec_service._build_document_url("0000320193", "0000320193-23-000106", "aapl-20230930.htm")
        assert "320193" in url
        assert "000032019323000106" in url
        assert "aapl-20230930.htm" in url

class TestFilingAnalyzer:
    def test_prompt_suite_integrity(self, analyzer):
        """Verify the forensic prompt suite is populated."""
        from app.services.filing_analyzer import FORENSIC_PROMPT_SUITE
        assert "accounting_forensics" in FORENSIC_PROMPT_SUITE
        assert "Sloan Ratio" in FORENSIC_PROMPT_SUITE["accounting_forensics"]

    @pytest.mark.asyncio
    @patch("app.services.rate_limiter_sqlite.rate_limiter.is_at_limit")
    async def test_rate_limit_handling(self, mock_limit, analyzer):
        """Test that the analyzer respects the central SQLite rate limiter."""
        mock_limit.return_value = True
        
        with pytest.raises(RateLimitError) as exc:
            await analyzer.extract_red_flags("test text")
        
        assert "Rate limit exceeded" in str(exc.value)

    @pytest.mark.asyncio
    @patch("app.services.rate_limiter_sqlite.rate_limiter.is_at_limit", return_value=False)
    @patch("app.services.rate_limiter_sqlite.rate_limiter.record_call")
    async def test_analysis_flow(self, mock_record, mock_limit, analyzer):
        """Test the analysis flow calls the Gemini client and records usage."""
        # Mock the Gemini client response
        mock_response = MagicMock()
        mock_response.text = "Identified potential revenue recognition shift in Note 3."
        
        # Mock the ASYNC client call using AsyncMock
        analyzer.client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        result = await analyzer.extract_red_flags("fake filing text")
        
        assert "revenue recognition" in result.response.lower()
        assert mock_record.called
        # Check that we used the correct model
        assert result.model == "gemini-2.5-flash"
