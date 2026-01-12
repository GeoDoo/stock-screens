"""SEC EDGAR filings service with PDF generation.

Fetches SEC filings and converts HTML to PDF using headless Chrome (playwright).
PDFs are cached in SQLite to avoid repeated expensive conversions.
"""
import logging
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Dict, Any

import httpx
from playwright.async_api import async_playwright

from app.services.filings_repository import get_filings_repository

logger = logging.getLogger(__name__)


class SECFilingsError(Exception):
    """Error fetching or processing SEC filings."""
    pass


@dataclass
class Filing:
    """SEC filing metadata."""
    accession_number: str
    form_type: str
    filing_date: date
    description: str
    document_url: str
    document_name: str  # e.g., "aapl-20230930.htm"
    cik: str
    ticker: str

    @property
    def viewer_url(self) -> str:
        """URL to SEC filing folder (lists all documents)."""
        clean_accession = self.accession_number.replace("-", "")
        cik_num = self.cik.lstrip("0")
        # Link to folder instead of -index.htm (more reliable, shows all documents)
        return f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{clean_accession}/"


class SECFilingsService:
    """
    Service for fetching SEC EDGAR filings and generating PDFs.
    
    SEC API requires User-Agent header with contact info.
    Rate limit: 10 requests/second.
    
    PDF generation uses headless Chrome via playwright.
    """
    
    BASE_URL = "https://data.sec.gov"
    TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
    
    def __init__(self, user_agent: str = "StockScreens support@stockscreens.app"):
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }
        self._cik_cache: Dict[str, str] = {}
        self._ticker_map: Optional[Dict[str, str]] = None
    
    async def _request(self, url: str, accept: str = "application/json") -> httpx.Response:
        """Make HTTP request with proper headers."""
        headers = {**self.headers, "Accept": accept}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response
    
    async def _load_ticker_map(self) -> Dict[str, str]:
        """Load ticker to CIK mapping from SEC."""
        if self._ticker_map is not None:
            return self._ticker_map
        
        try:
            response = await self._request(self.TICKER_URL)
            data = response.json()
            # Build ticker -> CIK map
            self._ticker_map = {}
            for item in data.values():
                ticker = item.get("ticker", "").upper()
                cik = str(item.get("cik_str", "")).zfill(10)
                if ticker and cik:
                    self._ticker_map[ticker] = cik
            return self._ticker_map
        except Exception as e:
            raise SECFilingsError(f"Failed to load ticker mapping: {e}")
    
    async def _get_cik(self, ticker: str) -> str:
        """Get CIK for a ticker symbol."""
        ticker = ticker.upper().strip().replace(".", "-")
        
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]
        
        ticker_map = await self._load_ticker_map()
        cik = ticker_map.get(ticker)
        
        if not cik:
            raise SECFilingsError(f"Ticker '{ticker}' not found in SEC database")
        
        self._cik_cache[ticker] = cik
        return cik
    
    def _build_document_url(self, cik: str, accession: str, document: str) -> str:
        """Build URL to SEC filing document."""
        cik_num = cik.lstrip("0")
        accession_clean = accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession_clean}/{document}"
    
    def _parse_filings_array(
        self,
        filings_data: Dict[str, List],
        cik: str,
        ticker: str,
        form_types: Optional[List[str]],
        limit: int,
        existing: List[Filing],
    ) -> List[Filing]:
        """Parse filings from a SEC submissions array."""
        filings = list(existing)
        
        accessions = filings_data.get("accessionNumber", [])
        forms = filings_data.get("form", [])
        dates = filings_data.get("filingDate", [])
        documents = filings_data.get("primaryDocument", [])
        descriptions = filings_data.get("primaryDocDescription", [])
        
        for i in range(len(accessions)):
            if len(filings) >= limit:
                break
            
            form_type = forms[i] if i < len(forms) else ""
            
            # Filter by form type if specified
            if form_types and form_type not in form_types:
                continue
            
            try:
                filing_date = date.fromisoformat(dates[i]) if i < len(dates) else date.today()
            except ValueError:
                continue
            
            accession = accessions[i]
            document = documents[i] if i < len(documents) else ""
            description = descriptions[i] if i < len(descriptions) else form_type
            
            filings.append(Filing(
                accession_number=accession,
                form_type=form_type,
                filing_date=filing_date,
                description=description or form_type,
                document_url=self._build_document_url(cik, accession, document),
                document_name=document,
                cik=cik,
                ticker=ticker,
            ))
        
        return filings

    async def get_filings(
        self,
        ticker: str,
        form_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Filing]:
        """
        Get SEC filings for a company.
        
        Fetches from both recent filings and historical filing archives
        to ensure complete coverage (e.g., all 10-Ks since IPO).
        
        Args:
            ticker: Stock ticker symbol
            form_types: Filter by form types (e.g., ["10-K", "10-Q"])
            limit: Maximum filings to return
            
        Returns:
            List of Filing objects
        """
        cik = await self._get_cik(ticker)
        ticker = ticker.upper().strip()
        
        url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
        response = await self._request(url)
        data = response.json()
        
        # Start with recent filings
        recent = data.get("filings", {}).get("recent", {})
        filings = self._parse_filings_array(recent, cik, ticker, form_types, limit, [])
        
        # If filtering and haven't hit limit, fetch from older filing archives
        if form_types and len(filings) < limit:
            older_files = data.get("filings", {}).get("files", [])
            
            for file_info in older_files:
                if len(filings) >= limit:
                    break
                    
                file_name = file_info.get("name")
                if not file_name:
                    continue
                
                try:
                    older_url = f"{self.BASE_URL}/submissions/{file_name}"
                    older_response = await self._request(older_url)
                    older_data = older_response.json()
                    filings = self._parse_filings_array(
                        older_data, cik, ticker, form_types, limit, filings
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch older filings from {file_name}: {e}")
        
        return filings
    
    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Get company information from SEC."""
        cik = await self._get_cik(ticker)
        
        url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
        response = await self._request(url)
        data = response.json()
        
        return {
            "cik": cik,
            "name": data.get("name", ""),
            "ticker": ticker.upper(),
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
        }
    
    async def get_filing_html(self, document_url: str) -> str:
        """Fetch SEC filing HTML content with SEC-compliant headers."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    document_url,
                    headers={
                        # SEC requires User-Agent with email for programmatic access
                        "User-Agent": self.headers["User-Agent"],
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            raise SECFilingsError(f"Failed to fetch filing HTML: {e}")
    
    async def get_filing_pdf(
        self,
        document_url: str,
        *,
        ticker: Optional[str] = None,
        cik: Optional[str] = None,
        accession_number: Optional[str] = None,
        form_type: Optional[str] = None,
        filing_date: Optional[date] = None,
        document_name: Optional[str] = None,
        use_cache: bool = True,
    ) -> bytes:
        """
        Convert SEC filing HTML to PDF.
        
        Checks cache first if metadata is provided. Stores result in cache
        for future requests.
        
        Args:
            document_url: URL to SEC filing HTML document
            ticker: Stock ticker (for caching)
            cik: Company CIK (for caching)
            accession_number: Filing accession (for caching)
            form_type: Form type (for caching)
            filing_date: Filing date (for caching)
            document_name: Document filename (for caching)
            use_cache: Whether to use cache (default True)
            
        Returns:
            PDF bytes
        """
        repo = get_filings_repository()
        
        # Check cache if we have the required identifiers
        if use_cache and cik and accession_number and document_name:
            cached = repo.get_pdf(cik, accession_number, document_name)
            if cached:
                logger.info(f"Returning cached PDF for {document_name}")
                return cached
        
        # Generate PDF
        try:
            # Fetch HTML ourselves with SEC-compliant headers
            html_content = await self.get_filing_html(document_url)
            
            # Get base URL for relative links (images, CSS, etc.)
            base_url = document_url.rsplit("/", 1)[0] + "/"
            
            # Inject base tag so relative URLs resolve correctly
            if "<head>" in html_content:
                html_content = html_content.replace(
                    "<head>", 
                    f'<head><base href="{base_url}">'
                )
            elif "<HEAD>" in html_content:
                html_content = html_content.replace(
                    "<HEAD>", 
                    f'<HEAD><base href="{base_url}">'
                )
            
            async with async_playwright() as p:
                # Chromium required for PDF generation
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1280, "height": 900})
                
                # Load our fetched HTML directly
                await page.set_content(html_content, wait_until="networkidle")
                
                # Give page time to render fully
                await page.wait_for_timeout(2000)
                
                # Generate PDF
                pdf_bytes = await page.pdf(
                    format="Letter",
                    margin={
                        "top": "0.5in",
                        "right": "0.5in", 
                        "bottom": "0.5in",
                        "left": "0.5in",
                    },
                    print_background=True,
                    scale=0.65,  # Scale down to fit tables
                )
                
                await browser.close()
            
            # Cache the result if we have metadata
            if (use_cache and ticker and cik and accession_number 
                    and form_type and filing_date and document_name):
                repo.save_pdf(
                    ticker=ticker,
                    cik=cik,
                    accession_number=accession_number,
                    form_type=form_type,
                    filing_date=filing_date,
                    document_name=document_name,
                    pdf_data=pdf_bytes,
                )
                logger.info(f"Cached PDF for {ticker} {form_type} ({document_name})")
            
            return pdf_bytes
                
        except SECFilingsError:
            raise
        except Exception as e:
            logger.error(f"PDF generation failed for {document_url}: {e}")
            raise SECFilingsError(f"Failed to generate PDF: {e}")


# Shared service instance
sec_filings_service = SECFilingsService()
