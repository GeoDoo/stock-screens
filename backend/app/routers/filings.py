"""SEC filings API with PDF download.

Phase 1: Filings Viewer with PDF generation.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.sec_filings import sec_filings_service, SECFilingsError

router = APIRouter(prefix="/api/filings", tags=["filings"])


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


@router.get("/pdf/{cik}/{accession_number}/{document}")
async def download_filing_pdf(
    cik: str,
    accession_number: str,
    document: str,
):
    """
    Download SEC filing as PDF.
    
    Converts the SEC HTML filing to PDF on-demand.
    
    Args:
        cik: Company CIK number
        accession_number: Filing accession number
        document: Document filename (e.g., "aapl-20230930.htm")
    """
    # Build the SEC document URL
    cik_num = cik.lstrip("0")
    accession_clean = accession_number.replace("-", "")
    document_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession_clean}/{document}"
    
    try:
        pdf_bytes = await sec_filings_service.get_filing_pdf(document_url)
        
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
