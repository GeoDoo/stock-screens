"""SEC filings API with PDF download.

Phase 1: Filings Viewer with PDF generation.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from fastapi.responses import Response

from app.services.sec_filings import sec_filings_service, SECFilingsError
from app.services.filing_analyzer import get_filing_analyzer, AnalyzerError
from app.services.filing_parser import FilingParser

router = APIRouter(prefix="/api/filings", tags=["filings"])
parser = FilingParser()


@router.get("/sections")
async def get_filing_sections(
    document_url: str = Query(..., description="SEC URL of the filing HTML"),
):
    """
    Extract major sections (Items) from an SEC filing.
    """
    try:
        html_content = await sec_filings_service.get_filing_html(document_url)
        sections = parser.extract_sections(html_content)
        
        return {
            "sections": list(sections.keys()),
            "section_lengths": {k: len(v) for k, v in sections.items()},
            "count": len(sections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-section")
async def analyze_filing_section(
    ticker: str = Query(..., description="Stock ticker symbol"),
    document_url: str = Query(..., description="SEC URL of the filing HTML"),
    section_name: str = Query(..., description="Name of the section to analyze (e.g., 'Item 7')"),
    query: Optional[str] = Query(None, description="Optional custom query for this section"),
):
    """
    Run analysis on a specific section of a filing.
    """
    analyzer = get_filing_analyzer()
    
    try:
        html_content = await sec_filings_service.get_filing_html(document_url)
        section_text = parser.get_section(html_content, section_name)
        
        if not section_text:
            raise HTTPException(status_code=404, detail=f"Section '{section_name}' not found in filing")
            
        if query:
            result = await analyzer.analyze(section_text, query)
        else:
            # Default analysis for the section
            result = await analyzer.analyze(
                section_text, 
                f"Analyze this {section_name} for any material risks or accounting shifts."
            )
            
        return {
            "ticker": ticker.upper(),
            "section": section_name,
            "query": result.query,
            "analysis": result.response,
            "timestamp": result.timestamp.isoformat(),
            "model": result.model
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-sections")
async def compare_filing_sections(
    ticker: str = Query(..., description="Stock ticker symbol"),
    current_url: str = Query(..., description="SEC URL of current filing"),
    previous_url: str = Query(..., description="SEC URL of previous filing"),
    section_name: str = Query(..., description="Name of section to compare"),
):
    """
    Compare the same section across two filings (Year-over-Year).
    """
    analyzer = get_filing_analyzer()
    
    try:
        current_html = await sec_filings_service.get_filing_html(current_url)
        previous_html = await sec_filings_service.get_filing_html(previous_url)
        
        current_text = parser.get_section(current_html, section_name)
        previous_text = parser.get_section(previous_html, section_name)
        
        if not current_text or not previous_text:
            raise HTTPException(status_code=404, detail=f"Section '{section_name}' not found in one or both filings")
            
        result = await analyzer.compare_filings(current_text, previous_text, section_name)
        
        return {
            "ticker": ticker.upper(),
            "section": section_name,
            "query": result.query,
            "analysis": result.response,
            "timestamp": result.timestamp.isoformat(),
            "model": result.model
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}")
async def get_filings(
    ticker: str,
    form_types: Optional[List[str]] = Query(
        None,
        description="Filter by form types (e.g., 10-K, 10-Q, 8-K)",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=2000,
        description="Maximum filings to return (higher limits for filtered searches)",
    ),
):
    """
    Get SEC filings for a company.
    
    Returns filing metadata with URLs to documents.
    Use the /pdf endpoint to download filings as PDF.
    """
    try:
        filings = await sec_filings_service.get_filings(
            ticker=ticker,
            form_types=form_types,
            limit=limit,
        )
        
        # Get company info
        company_info = await sec_filings_service.get_company_info(ticker)
        
        return {
            "ticker": ticker.upper(),
            "company_name": company_info.get("name"),
            "cik": company_info.get("cik"),
            "filings": [
                {
                    "accession_number": f.accession_number,
                    "form_type": f.form_type,
                    "filing_date": f.filing_date.isoformat(),
                    "description": f.description,
                    "document_url": f.document_url,
                    "document_name": f.document_name,
                    "viewer_url": f.viewer_url,
                }
                for f in filings
            ],
            "count": len(filings),
        }
        
    except SECFilingsError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/info")
async def get_company_info(ticker: str):
    """Get SEC company information."""
    try:
        info = await sec_filings_service.get_company_info(ticker)
        return info
    except SECFilingsError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/crawl")
async def crawl_filings(
    ticker: str,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a deep crawl of a company's filing history.
    
    This fetches all historical archives (10+ years) and persists
    them to the local database for offline forensic analysis.
    
    Returns immediately and runs in the background.
    """
    try:
        # Verify ticker exists before starting background task
        await sec_filings_service.get_company_info(ticker)
        
        # Start background crawl
        background_tasks.add_task(sec_filings_service.crawl_ticker_history, ticker)
        
        return {
            "ticker": ticker.upper(),
            "status": "crawling_started",
            "message": f"Filing history crawl for {ticker.upper()} started in background."
        }
    except SECFilingsError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf/{ticker}/{cik}/{accession_number}/{form_type}/{filing_date}/{document}")
async def download_filing_pdf(
    ticker: str,
    cik: str,
    accession_number: str,
    form_type: str,
    filing_date: str,
    document: str,
):
    """
    Download SEC filing as PDF.
    
    Converts the SEC HTML filing to PDF on-demand. PDFs are cached
    in the database to avoid repeated conversions.
    
    Args:
        ticker: Stock ticker symbol
        cik: Company CIK number
        accession_number: Filing accession number
        form_type: SEC form type (e.g., "10-K")
        filing_date: Filing date (YYYY-MM-DD)
        document: Document filename (e.g., "aapl-20230930.htm")
    """
    from datetime import date as date_type
    
    # Build the SEC document URL
    cik_num = cik.lstrip("0")
    accession_clean = accession_number.replace("-", "")
    document_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession_clean}/{document}"
    
    # Parse filing date
    try:
        parsed_date = date_type.fromisoformat(filing_date)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {filing_date}")
    
    try:
        pdf_bytes = await sec_filings_service.get_filing_pdf(
            document_url,
            ticker=ticker.upper(),
            cik=cik,
            accession_number=accession_number,
            form_type=form_type,
            filing_date=parsed_date,
            document_name=document,
        )
        
        # Generate filename
        pdf_filename = document.rsplit(".", 1)[0] + ".pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_filename}"'
            }
        )
        
    except SECFilingsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/analyze")
async def analyze_filing(
    ticker: str,
    document_url: str = Query(..., description="SEC URL of the filing HTML"),
    query: Optional[str] = Query(None, description="Optional custom query for analysis"),
):
    """
    Run forensic analysis on a specific SEC filing.
    
    This uses the 'Institutional-Grade' prompt suite to detect shenanigans.
    """
    analyzer = get_filing_analyzer()
    
    try:
        # 1. Fetch the HTML (cached by SECFilingsService logic if we use it)
        html_content = await sec_filings_service.get_filing_html(document_url)
        
        # 2. Run Forensic Scan
        if query:
            result = await analyzer.analyze(html_content, query)
        else:
            result = await analyzer.extract_red_flags(html_content)
            
        return {
            "ticker": ticker.upper(),
            "query": result.query,
            "analysis": result.response,
            "timestamp": result.timestamp.isoformat(),
            "model": result.model
        }
        
    except (SECFilingsError, AnalyzerError) as e:
        raise HTTPException(status_code=500, detail=str(e))
