import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock
from app.services.filing_analyzer import AnalysisResult
from datetime import datetime, timezone

client = TestClient(app)

def test_compare_sections_response_includes_query():
    """
    Regression test: Ensure /api/filings/compare-sections response includes 'query' field.
    """
    # Mock services to avoid actual API calls
    with patch("app.routers.filings.sec_filings_service") as mock_sec_service:
        with patch("app.routers.filings.parser") as mock_parser:
            with patch("app.routers.filings.get_filing_analyzer") as mock_get_analyzer:
                
                # Setup mocks
                mock_sec_service.get_filing_html = AsyncMock(return_value="<html></html>")
                mock_parser.get_section.return_value = "Section Text"
                
                mock_analyzer = AsyncMock()
                mock_analyzer.compare_filings.return_value = AnalysisResult(
                    query="Mock Query",
                    response="Mock Response",
                    model="Mock Model",
                    timestamp=datetime.now(timezone.utc)
                )
                mock_get_analyzer.return_value = mock_analyzer
                
                # Make request
                response = client.post(
                    "/api/filings/compare-sections",
                    params={
                        "ticker": "AAPL",
                        "current_url": "https://example.com/current",
                        "previous_url": "https://example.com/previous",
                        "section_name": "Item 7"
                    }
                )
                
                assert response.status_code == 200
                json_data = response.json()
                assert "query" in json_data
                assert json_data["query"] == "Mock Query"
                assert "analysis" in json_data
                assert "section" in json_data
                assert json_data["section"] == "Item 7"
