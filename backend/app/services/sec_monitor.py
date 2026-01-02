"""SEC EDGAR monitoring service for spinoff detection."""

import logging
from datetime import date, datetime
from typing import Optional

import httpx

from app.config import settings
from app.models.spinoff import Spinoff, SpinoffStatus

logger = logging.getLogger(__name__)


# Form types that indicate spinoffs
SPINOFF_FORM_TYPES = ["10-12B", "10-12G", "10"]


class SECMonitorService:
    """Service for monitoring SEC filings for spinoffs."""

    SEC_EDGAR_BASE = "https://www.sec.gov"
    SEC_SEARCH_API = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self):
        self.headers = {
            "User-Agent": settings.sec_user_agent,
            "Accept": "application/json",
        }

    async def parse_spinoff_filing(self, filing: dict) -> Optional[Spinoff]:
        """
        Parse a SEC filing to extract spinoff information.
        
        Args:
            filing: Dictionary with filing data from SEC
        
        Returns:
            Spinoff object if this is a valid spinoff filing, None otherwise
        """
        form_type = filing.get("form", "")
        
        # Check if this is a spinoff-related form
        if not any(form_type.startswith(ft) for ft in SPINOFF_FORM_TYPES):
            return None
        
        company_name = filing.get("company_name", "Unknown")
        filing_date_str = filing.get("filing_date", "")
        file_url = filing.get("file_url", "")
        
        # Parse filing date
        try:
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            filing_date = date.today()
        
        # Validate URL (security)
        if file_url and not file_url.startswith(self.SEC_EDGAR_BASE):
            logger.warning(f"Invalid SEC URL rejected: {file_url}")
            file_url = None
        
        return Spinoff(
            spinoff_name=company_name,
            parent_symbol="",  # Will need to be extracted from filing
            parent_name="Unknown",  # Will need to be extracted from filing
            sec_filing_url=file_url,
            sec_filing_date=filing_date,
            sec_filing_type=form_type,
            announcement_date=filing_date,
            status=SpinoffStatus.ANNOUNCED,
        )

    async def _fetch_sec_filings(
        self,
        form_types: list[str],
        days: int = 30,
    ) -> dict:
        """
        Fetch filings from SEC EDGAR search API.
        
        Args:
            form_types: List of form types to search for
            days: Number of days to look back
        
        Returns:
            Raw API response dictionary
        """
        from datetime import timedelta
        
        start_date = date.today() - timedelta(days=days)
        
        # Build search query for SEC full-text search API
        query = {
            "q": " OR ".join(f'formType:"{ft}"' for ft in form_types),
            "dateRange": "custom",
            "startdt": start_date.strftime("%Y-%m-%d"),
            "enddt": date.today().strftime("%Y-%m-%d"),
            "forms": form_types,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.SEC_SEARCH_API,
                params=query,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_recent_spinoff_filings(self, days: int = 30) -> list[dict]:
        """
        Get recent spinoff-related filings from SEC.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of filing dictionaries
        """
        try:
            response = await self._fetch_sec_filings(SPINOFF_FORM_TYPES, days)
            
            filings = []
            hits = response.get("hits", {}).get("hits", [])
            
            for hit in hits:
                source = hit.get("_source", {})
                filings.append({
                    "form": source.get("form", ""),
                    "company_name": source.get("display_names", ["Unknown"])[0],
                    "filing_date": source.get("file_date", ""),
                    "file_number": source.get("file_num", ""),
                })
            
            return filings
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch SEC filings: {e}")
            return []

