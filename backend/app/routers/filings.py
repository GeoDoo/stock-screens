"""SEC filings API with PDF download.

Phase 1: Filings Viewer with PDF generation.
"""
import os
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from fastapi.responses import Response

from app.services.sec_filings import sec_filings_service, SECFilingsError
from app.services.filing_analyzer import get_filing_analyzer, AnalyzerError, RateLimitError as LLMRateLimitError
from app.services.filing_parser import FilingParser
from app.services.filings_repository import get_filings_repository
from app.services.stock_data_client import StockDataClient
from app.services.base_provider import RateLimitError as ProviderRateLimitError
from app.services.data_extractor import DataExtractor
from app.services.financial_audit import FinancialAuditService
from app.services.data_adapter import stock_data_to_legacy
from app.schemas.forensic import FilingForensicResponse, ForensicReport, QuantitativeAudit

router = APIRouter(prefix="/api/filings", tags=["filings"])
parser = FilingParser()

# Get API keys from environment
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

def get_stock_client(provider: str = "fmp"):
    """Get a StockDataClient for numerical analysis."""
    if provider == "fmp" and FMP_API_KEY:
        from app.services.fmp_provider import FMPProvider
        return StockDataClient(providers=[FMPProvider(FMP_API_KEY)])
    from app.services.yahoo_provider import YahooProvider
    return StockDataClient(providers=[YahooProvider()])


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
        if isinstance(e, (LLMRateLimitError, ProviderRateLimitError)):
            raise HTTPException(status_code=429, detail=str(e))
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-sections")
async def compare_filing_sections(
    ticker: str = Query(..., description="Stock ticker symbol"),
    current_url: str = Query(..., description="SEC URL of current filing"),
    previous_url: str = Query(..., description="SEC URL of previous filing"),
    section_name: Optional[str] = Query(None, description="Name of section to compare (omit for full filing)"),
):
    """
    Compare the same section across two filings (Year-over-Year).
    """
    analyzer = get_filing_analyzer()
    
    try:
        current_html = await sec_filings_service.get_filing_html(current_url)
        previous_html = await sec_filings_service.get_filing_html(previous_url)
        
        # If section_name is provided and not empty, extract it. Otherwise use full text.
        if section_name and section_name.strip():
            current_text = parser.get_section(current_html, section_name)
            previous_text = parser.get_section(previous_html, section_name)
            
            if not current_text or not previous_text:
                raise HTTPException(status_code=404, detail=f"Section '{section_name}' not found in one or both filings")
            
            compare_label = section_name
        else:
            current_text = parser.clean_html(current_html)
            previous_text = parser.clean_html(previous_html)
            compare_label = "entire filing"
            
        result = await analyzer.compare_filings(current_text, previous_text, compare_label)
        
        return {
            "ticker": ticker.upper(),
            "section": compare_label,
            "query": result.query,
            "analysis": result.response,
            "timestamp": result.timestamp.isoformat(),
            "model": result.model
        }
    except Exception as e:
        if isinstance(e, (LLMRateLimitError, ProviderRateLimitError)):
            raise HTTPException(status_code=429, detail=str(e))
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/forensic-audit", response_model=FilingForensicResponse)
async def run_forensic_audit(
    ticker: str,
    document_url: str = Query(..., description="SEC URL of the filing HTML"),
    accession_number: Optional[str] = Query(None, description="SEC accession number for persistence"),
    provider: str = Query("fmp", description="Provider for numerical analysis"),
):
    """
    Perform a complete institutional-grade forensic audit of a filing.
    Returns a structured report with textual red flags and quantitative statement analysis.
    """
    analyzer = get_filing_analyzer()
    from app.services.logging_config import logger
    from app.services.rate_limiter_sqlite import rate_limiter
    
    try:
        # 1. TEXTUAL AUDIT (LLM)
        html_content = await sec_filings_service.get_filing_html(document_url)
        text_content = parser.clean_html(html_content)
        report = await analyzer.analyze_forensic(text_content)
        
        # 2. QUANTITATIVE AUDIT (NUMBERS FROM THE FILE)
        report.quantitative_audit = QuantitativeAudit(sloan_ratio=None, altman_z_score=None, beneish_m_score=None, findings=[])
        client = None
        extractor = None
        try:
            # Extract numerical facts directly from the iXBRL in the HTML (Source of Truth)
            from app.services.data_adapter import ixbrl_facts_to_legacy
            ixbrl_facts_by_date = parser.extract_ixbrl_facts(html_content)
            
            # ... logic to fetch from API or file ...
            if ixbrl_facts_by_date:
                logger.info("file_sourced_quantitative_audit_started", ticker=ticker)
                legacy_data = ixbrl_facts_to_legacy(ixbrl_facts_by_date)
                
                # Market Cap isn't in XBRL usually, try a quick API hit just for the denominator of Z-Score
                try:
                    client = get_stock_client(provider)
                    if not await rate_limiter.is_api_limited(provider):
                        stock_data = await client.get_stock_data(ticker)
                        legacy_data["profile"]["marketCap"] = stock_data.profile.market_cap
                        legacy_data["profile"]["symbol"] = ticker.upper()
                        legacy_data["profile"]["price"] = stock_data.profile.price
                except ProviderRateLimitError:
                    logger.warning("api_metadata_fetch_rate_limited", ticker=ticker)
                    await rate_limiter.mark_api_limited(provider)
                except Exception as e:
                    logger.warning("api_metadata_fetch_failed", ticker=ticker, error=str(e))
                
                extractor = DataExtractor(legacy_data)
                auditor = FinancialAuditService(extractor)
                quant_results = auditor.analyze_statements()
                
                report.quantitative_audit = QuantitativeAudit(
                    sloan_ratio=quant_results.get("sloan_ratio"),
                    altman_z_score=quant_results.get("altman_z_score", {}).get("score") if quant_results.get("altman_z_score") else None,
                    beneish_m_score=quant_results.get("beneish_m_score", {}).get("score") if quant_results.get("beneish_m_score") else None,
                    liquidity_ratios=quant_results.get("liquidity_ratios", {}),
                    solvency_ratios=quant_results.get("solvency_ratios", {}),
                    efficiency_ratios=quant_results.get("efficiency_ratios", {}),
                    profitability_ratios=quant_results.get("profitability_ratios", {}),
                    accounting_corrections=quant_results.get("accounting_corrections", []),
                    findings=[f"[FILE SOURCED] {f}" for f in quant_results.get("quantitative_findings", [])]
                )
            else:
                # Fallback to API data if no iXBRL tags found (older filings)
                logger.info("no_ixbrl_found_falling_back_to_api", ticker=ticker)
                client = get_stock_client(provider)
                if await rate_limiter.is_api_limited(provider):
                    reset_in = await rate_limiter.get_time_until_reset(provider)
                    wait_msg = f" after {reset_in}s" if reset_in else ""
                    report.quantitative_audit.findings = [f"Numerical audit limited to text-scan due to API limits.{wait_msg}"]
                else:
                    api_data = await client.get_stock_data(ticker)
                    legacy_data = stock_data_to_legacy(api_data)
                    extractor = DataExtractor(legacy_data)
                    auditor = FinancialAuditService(extractor)
                    quant_results = auditor.analyze_statements()
                    
                    report.quantitative_audit = QuantitativeAudit(
                        sloan_ratio=quant_results.get("sloan_ratio"),
                        altman_z_score=quant_results.get("altman_z_score", {}).get("score") if quant_results.get("altman_z_score") else None,
                        beneish_m_score=quant_results.get("beneish_m_score", {}).get("score") if quant_results.get("beneish_m_score") else None,
                        liquidity_ratios=quant_results.get("liquidity_ratios", {}),
                        solvency_ratios=quant_results.get("solvency_ratios", {}),
                        efficiency_ratios=quant_results.get("efficiency_ratios", {}),
                        profitability_ratios=quant_results.get("profitability_ratios", {}),
                        accounting_corrections=quant_results.get("accounting_corrections", []),
                        findings=[f"[API FALLBACK] {f}" for f in quant_results.get("quantitative_findings", [])]
                    )

            # Generate Execution Risk Matrix if enough data
            if client and extractor:
                try:
                    from app.services.valuation_service import ValuationService
                    valuation_service = ValuationService(client)
                    # We need a WACC for the matrix. Try to calculate or use fallback.
                    wacc = 0.10 # Default fallback
                    try:
                        # Attempt a quick WACC calculation
                        risk_free = await client.get_treasury_rate()
                        beta = extractor.beta() or 1.0
                        cost_of_debt = extractor.cost_of_debt(risk_free) or (risk_free + 0.02)
                        from app.services.wacc_calculator import WACCCalculator
                        wacc_calc = WACCCalculator(
                            risk_free_rate=risk_free,
                            beta=beta,
                            market_risk_premium=extractor.market_risk_premium(),
                            cost_of_debt=cost_of_debt,
                            tax_rate=extractor.tax_rate() or 0.25,
                            market_cap=extractor.market_cap() or 1e9,
                            total_debt=extractor.total_debt() or 0
                        )
                        wacc = wacc_calc.calculate()
                    except Exception as e:
                        logger.debug("wacc_calculation_failed_for_matrix", error=str(e))
                    
                    matrix = await valuation_service.calculate_sensitivity_from_extractor(extractor, wacc)
                    report.quantitative_audit.margin_growth_sensitivity = matrix
                except Exception as e:
                    logger.warning("matrix_generation_failed", ticker=ticker, error=str(e))
            
        except (LLMRateLimitError, ProviderRateLimitError) as e:
            logger.warning("quantitative_audit_rate_limited", ticker=ticker, provider=provider)
            # Graceful degradation: include a finding that quantitative data was rate-limited
            error_msg = str(e)
            if "Retry after" in error_msg:
                try:
                    # Clean up the message if it has long floats
                    parts = error_msg.split("after ")
                    if len(parts) > 1:
                        seconds = float(parts[1].split("s")[0])
                        error_msg = f"Rate limit reached. Retry after {int(seconds)}s."
                except Exception:
                    pass
            
            report.quantitative_audit = QuantitativeAudit(
                sloan_ratio=None,
                altman_z_score=None,
                beneish_m_score=None,
                findings=[f"Numerical audit unavailable: {error_msg}"]
            )
        except Exception as e:
            logger.warning("quantitative_audit_failed", ticker=ticker, error=str(e))
            # Don't fail the whole audit if numerical data is missing
        
        # 3. PERSISTENCE: Save to DB if accession_number is provided
        if accession_number:
            repo = get_filings_repository()
            await repo.update_forensic_report(
                accession_number=accession_number,
                consistency_score=report.accounting_consistency_score,
                reported_eps=report.reported_eps,
                forensic_eps_adjustment=report.forensic_eps_adjustment,
                report_json=report.model_dump_json()
            )
        
        return FilingForensicResponse(ticker=ticker.upper(), report=report)
        
    except (SECFilingsError, AnalyzerError) as e:
        if isinstance(e, (LLMRateLimitError, ProviderRateLimitError)):
            raise HTTPException(status_code=429, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/{ticker}/forensic-history")
async def get_forensic_history(ticker: str):
    """
    Get the historical forensic audit results for a company.
    Used to build the Forensic Timeline dashboard.
    """
    repo = get_filings_repository()
    try:
        # Get audited 10-Ks
        metadata = await repo.list_metadata(ticker=ticker, form_type="10-K", limit=10)
        
        history = []
        for m in metadata:
            if m.get("consistency_score") is not None:
                history.append({
                    "accession_number": m["accession_number"],
                    "filing_date": m["filing_date"],
                    "consistency_score": m["consistency_score"],
                    "report": m.get("forensic_report_json"),
                    "form_type": m["form_type"]
                })
        
        return {
            "ticker": ticker.upper(),
            "history": history,
            "count": len(history)
        }
    except Exception as e:
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
        
        response_data = {
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
                    "consistency_score": None,
                    "sentiment_score": None,
                    "parsed_status": "pending",
                }
                for f in filings
            ],
            "count": len(filings),
        }

        # Merge with local metadata if available
        repo = get_filings_repository()
        local_metadata = await repo.list_metadata(ticker=ticker, limit=limit)
        local_map = {m["accession_number"]: m for m in local_metadata}
        
        for filing_dict in response_data["filings"]:
            acc = filing_dict["accession_number"]
            if acc in local_map:
                filing_dict["consistency_score"] = local_map[acc].get("consistency_score")
                filing_dict["parsed_status"] = local_map[acc].get("parsed_status")
                filing_dict["sentiment_score"] = local_map[acc].get("sentiment_score")
        
        return response_data
        
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
        
        # New: Also start background historical audit for the timeline
        background_tasks.add_task(sec_filings_service.audit_ticker_history, ticker)
        
        return {
            "ticker": ticker.upper(),
            "status": "crawling_started",
            "message": f"Filing history crawl and forensic audit for {ticker.upper()} started in background."
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
                "Content-Disposition": f'inline; filename="{pdf_filename}"'
            }
        )
        
    except SECFilingsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/analyze")
async def analyze_filing(
    ticker: str,
    document_url: str = Query(..., description="SEC URL of the filing HTML"),
    query: Optional[str] = Query(None, description="Optional custom query for analysis"),
    provider: str = Query("fmp", description="Provider for numerical analysis"),
):
    """
    Run forensic analysis on a specific SEC filing.
    
    This uses the 'Institutional-Grade' prompt suite to detect shenanigans.
    Now includes a fast quantitative audit (iXBRL) even if LLM is limited.
    """
    analyzer = get_filing_analyzer()
    from app.services.logging_config import logger
    from app.services.rate_limiter_sqlite import rate_limiter
    
    # 1. Fetch the HTML
    try:
        html_content = await sec_filings_service.get_filing_html(document_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch filing: {str(e)}")

    # 2. Fast Quantitative Audit (No LLM needed)
    quant_audit = QuantitativeAudit(sloan_ratio=None, altman_z_score=None, beneish_m_score=None, findings=[])
    try:
        from app.services.data_adapter import ixbrl_facts_to_legacy
        ixbrl_facts_by_date = parser.extract_ixbrl_facts(html_content)
        
        # If file has no iXBRL or extraction failed, try a quick API hit
        if not ixbrl_facts_by_date and not await rate_limiter.is_api_limited(provider):
            try:
                client = get_stock_client(provider)
                api_data = await client.get_stock_data(ticker)
                legacy_data = stock_data_to_legacy(api_data)
                extractor = DataExtractor(legacy_data)
                auditor = FinancialAuditService(extractor)
                quant_results = auditor.analyze_statements()
                
                quant_audit = QuantitativeAudit(
                    sloan_ratio=quant_results.get("sloan_ratio"),
                    altman_z_score=quant_results.get("altman_z_score", {}).get("score") if quant_results.get("altman_z_score") else None,
                    beneish_m_score=quant_results.get("beneish_m_score", {}).get("score") if quant_results.get("beneish_m_score") else None,
                    liquidity_ratios=quant_results.get("liquidity_ratios", {}),
                    solvency_ratios=quant_results.get("solvency_ratios", {}),
                    efficiency_ratios=quant_results.get("efficiency_ratios", {}),
                    profitability_ratios=quant_results.get("profitability_ratios", {}),
                    accounting_corrections=quant_results.get("accounting_corrections", []),
                    findings=[f"[API FALLBACK] {f}" for f in quant_results.get("quantitative_findings", [])]
                )
            except Exception as e:
                logger.warning("api_fallback_failed_for_scan", ticker=ticker, error=str(e))
        elif ixbrl_facts_by_date:
            legacy_data = ixbrl_facts_to_legacy(ixbrl_facts_by_date)
            
            # Try quick metadata hit for Altman Z-Score even in SCAN mode
            try:
                if not await rate_limiter.is_api_limited(provider):
                    client = get_stock_client(provider)
                    stock_data = await client.get_stock_data(ticker)
                    legacy_data["profile"]["marketCap"] = stock_data.profile.market_cap
                    legacy_data["profile"]["price"] = stock_data.profile.price
            except Exception:
                pass

            extractor = DataExtractor(legacy_data)
            auditor = FinancialAuditService(extractor)
            quant_results = auditor.analyze_statements()
            
            quant_audit = QuantitativeAudit(
                sloan_ratio=quant_results.get("sloan_ratio"),
                altman_z_score=quant_results.get("altman_z_score", {}).get("score") if quant_results.get("altman_z_score") else None,
                beneish_m_score=quant_results.get("beneish_m_score", {}).get("score") if quant_results.get("beneish_m_score") else None,
                liquidity_ratios=quant_results.get("liquidity_ratios", {}),
                solvency_ratios=quant_results.get("solvency_ratios", {}),
                efficiency_ratios=quant_results.get("efficiency_ratios", {}),
                profitability_ratios=quant_results.get("profitability_ratios", {}),
                accounting_corrections=quant_results.get("accounting_corrections", []),
                findings=[f"[FILE SOURCED] {f}" for f in quant_results.get("quantitative_findings", [])]
            )
    except Exception as e:
        logger.warning("scan_quantitative_audit_failed", ticker=ticker, error=str(e))

        # 3. Textual Forensic Scan (LLM)
    try:
        if query:
            result = await analyzer.analyze(html_content, query)
        else:
            result = await analyzer.extract_red_flags(html_content)
            
        return {
            "ticker": ticker.upper(),
            "query": result.query,
            "analysis": result.response,
            "timestamp": result.timestamp.isoformat(),
            "model": result.model,
            "quantitative_audit": quant_audit.model_dump() if quant_audit else None
        }
        
    except (LLMRateLimitError, ProviderRateLimitError) as e:
        # Graceful degradation
        logger.warning("scan_textual_analysis_rate_limited", ticker=ticker)
        
        error_msg = str(e)
        if "Retry after" in error_msg:
            try:
                parts = error_msg.split("after ")
                if len(parts) > 1:
                    seconds = float(parts[1].split("s")[0])
                    error_msg = f"Forensic AI is currently at its free-tier limit. Retry in {int(seconds)}s."
            except:
                pass

        return {
            "ticker": ticker.upper(),
            "query": query or "Forensic Red Flags",
            "analysis": f"### ⚠️ AI RATE LIMIT REACHED\n\n{error_msg}\n\nNumerical statement analysis is still available below.",
            "timestamp": date.today().isoformat(),
            "model": "rate-limited",
            "quantitative_audit": quant_audit.model_dump() if quant_audit else None
        }
    except AnalyzerError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")