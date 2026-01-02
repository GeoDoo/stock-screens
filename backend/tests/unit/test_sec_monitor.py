"""
Unit tests for SEC spinoff detection.

TDD: Writing tests ONE AT A TIME.
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.services.sec_monitor import SECMonitorService
from app.models.spinoff import Spinoff, SpinoffStatus


class TestSpinoffDetection:
    """Tests for detecting spinoffs from SEC filings."""

    @pytest.mark.asyncio
    async def test_parse_form_10_filing(self):
        """
        Test parsing a Form 10 (spinoff registration) filing.
        
        Form 10 is filed when a company registers as a new entity
        after being spun off from a parent.
        """
        service = SECMonitorService()
        
        # Mock SEC filing data
        mock_filing = {
            "form": "10-12B",
            "company_name": "SpinCo Inc.",
            "filing_date": "2025-01-02",
            "accession_number": "0001234567-25-000001",
            "file_url": "https://www.sec.gov/Archives/edgar/data/123456/000123456725000001/form10.htm",
        }
        
        result = await service.parse_spinoff_filing(mock_filing)
        
        assert result is not None
        assert result.spinoff_name == "SpinCo Inc."
        assert result.status == SpinoffStatus.ANNOUNCED

    @pytest.mark.asyncio
    async def test_fetch_recent_spinoff_filings(self):
        """
        Test fetching recent Form 10 filings from SEC EDGAR.
        
        This should query SEC's search API for recent spinoff-related filings.
        """
        service = SECMonitorService()
        
        # Mock the HTTP response
        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "form": "10-12B",
                            "display_names": ["Test Spinoff Corp"],
                            "file_date": "2025-01-02",
                            "file_num": "001-12345",
                        }
                    }
                ]
            }
        }
        
        with patch.object(service, "_fetch_sec_filings", return_value=mock_response):
            results = await service.get_recent_spinoff_filings(days=30)
        
        assert isinstance(results, list)

