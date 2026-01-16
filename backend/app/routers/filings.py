"""SEC filings API with PDF download.

Phase 1: Filings Viewer with PDF generation.
"""
import os
import asyncio
from datetime import date
from typing import List, Optional, Dict, Any

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
from app.services.ltm_calculator import LTMCalculator
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


async def _get_ltm_facts_if_needed(ticker: str, current_facts: List[Dict[str, Any]], document_url: str) -> List[Dict[str, Any]]:
    """Helper to reconstruct LTM facts if the current filing is a 10-Q."""
    from app.services.logging_config import logger
    
    latest_flow = next((f for f in sorted(current_facts, key=lambda x: (x["date"], x.get("duration", 0)), reverse=True) 
                      if f.get("duration", 0) > 0), None)
    
    if not latest_flow or latest_flow.get("duration", 0) >= 350:
        return current_facts

    logger.info("ltm_merging_started", ticker=ticker, latest_duration=latest_flow.get("duration"))
    try:
        # 1. Get filing history
        filings = await sec_filings_service.get_filings(ticker, form_types=["10-K", "10-Q"], limit=20)
        
        # 2. Find previous 10-K and previous matching 10-Q
        prev_10k = None
        prev_10q = None
        
        # Find current filing date to use as reference
        current_filing_date = date.today()
        for f in filings:
            if f.document_url == document_url:
                current_filing_date = f.filing_date
                break
        
        # Find previous 10-K
        for f in filings:
            if f.form_type == "10-K" and f.filing_date < current_filing_date:
                prev_10k = f
                break
        
        # Find previous matching 10-Q (same period last year)
        if prev_10k:
            current_period_end = date.fromisoformat(latest_flow["date"])
            
            for f in filings:
                # Look for a 10-Q filed around 1 year before current filing
                if f.form_type == "10-Q" and abs((f.filing_date - (current_filing_date.replace(year=current_filing_date.year - 1))).days) < 60:
                    prev_10q = f
                    break
        
        if prev_10k and prev_10q:
            logger.info("ltm_merging_fetching_historical", 
                      prev_10k=prev_10k.accession_number, 
                      prev_10q=prev_10q.accession_number)
            
            # 3. Fetch and parse
            h1 = await sec_filings_service.get_filing_html(prev_10k.document_url)
            h2 = await sec_filings_service.get_filing_html(prev_10q.document_url)
            
            facts_10k = parser.extract_ixbrl_facts(h1)
            facts_10q = parser.extract_ixbrl_facts(h2)
            
            # 4. Calculate LTM
            ltm_calc = LTMCalculator()
            ltm_fact_set = ltm_calc.calculate_ltm_facts(
                current_facts=current_facts,
                previous_fy_facts=facts_10k,
                previous_ytd_facts=facts_10q
            )
            
            if ltm_fact_set:
                current_facts.append(ltm_fact_set)
                logger.info("ltm_merging_success", date=ltm_fact_set["date"])
    except Exception as e:
        logger.warning("ltm_merging_failed", ticker=ticker, error=str(e))
    
    return current_facts


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
    accession_number: Optional[str] = Query(None, description="SEC accession number for persistence"),
    section_name: str = Query(..., description="Name of the section to analyze (e.g., 'Item 7')"),
    query: Optional[str] = Query(None, description="Optional custom query for this section"),
):
    """
    Run analysis on a specific section of a filing.
    """
    analyzer = get_filing_analyzer()
    repo = get_filings_repository()
    
    try:
        section_text = None
        
        # 1. Try to get from database first if accession_number provided
        if accession_number:
            cached_section = await repo.get_section(accession_number, section_name)
            if cached_section:
                section_text = cached_section["content_text"]
        
        # 2. Fallback to fetching and parsing if not in DB
        if not section_text:
            html_content = await sec_filings_service.get_filing_html(document_url)
            section_text = parser.get_section(html_content, section_name)
            
            # Save all sections if we had to fetch the full HTML anyway
            if accession_number and section_text:
                asyncio.create_task(sec_filings_service.save_filing_sections(accession_number, html_content))
        
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
        # 1. Fetch HTML
        html_content = await sec_filings_service.get_filing_html(document_url)
        
        # Save granular sections for forensic persistence
        if accession_number:
            asyncio.create_task(sec_filings_service.save_filing_sections(accession_number, html_content))
            
        text_content = parser.clean_html(html_content)
        
        # 2. TEXTUAL AUDIT (LLM) - With Graceful Degradation
        report = None
        try:
            report = await analyzer.analyze_forensic(text_content)
        except (LLMRateLimitError, ProviderRateLimitError) as e:
            logger.warning("forensic_llm_scan_rate_limited", ticker=ticker)
            error_msg = str(e)
            if "Retry after" in error_msg:
                try:
                    parts = error_msg.split("after ")
                    if len(parts) > 1:
                        seconds = float(parts[1].split("s")[0])
                        error_msg = f"Forensic AI is currently at its free-tier limit. Retry in {int(seconds)}s."
                except:
                    pass
            
            # Create graceful degradation report with correct RedFlagCategory schema
            report = ForensicReport(
                accounting_consistency_score=0,
                red_flags=[{
                    "category": "⚠️ AI Rate Limit",
                    "score": 5,
                    "severity": "Medium",
                    "findings": ["Forensic AI (LLM) reached rate limits. Textual analysis unavailable."],
                    "evidence_quotes": [error_msg]
                }],
                summary=f"Institutional Forensic Analysis: AI Rate Limit Reached. {error_msg} Numerical analysis is still available below.",
                reported_eps=None,
                forensic_eps_adjustment=0.0,
                adjustments=[],
                model="rate-limited"
            )
        except Exception as e:
            logger.error("forensic_llm_scan_failed", ticker=ticker, error=str(e))
            # Create error report with correct RedFlagCategory schema
            report = ForensicReport(
                accounting_consistency_score=0,
                red_flags=[{
                    "category": "Error",
                    "score": 10,
                    "severity": "Critical",
                    "findings": ["AI scan failed"],
                    "evidence_quotes": [str(e)]
                }],
                summary=f"Forensic scan failed: {str(e)}. Numerical analysis available below.",
                reported_eps=None,
                forensic_eps_adjustment=0.0,
                adjustments=[],
                model="error"
            )
        
        # 3. QUANTITATIVE AUDIT (SINGLE SOURCE OF TRUTH: FILE ONLY - NO API CALLS)
        report.quantitative_audit = QuantitativeAudit(sloan_ratio=None, altman_z_score=None, beneish_m_score=None, findings=[])
        extractor = None
        try:
            # Extract numerical facts directly from the iXBRL in the HTML (Source of Truth)
            from app.services.data_adapter import ixbrl_facts_to_legacy
            ixbrl_facts_by_period = parser.extract_ixbrl_facts(html_content)
            
            # LTM Data Merging (NOTES2.md Item #8)
            # Reconstruct TTM facts if we have 10-Q data
            if ixbrl_facts_by_period:
                ixbrl_facts_by_period = await _get_ltm_facts_if_needed(ticker, ixbrl_facts_by_period, document_url)

            if ixbrl_facts_by_period:
                logger.info("file_sourced_quantitative_audit_started", ticker=ticker)
                legacy_data = ixbrl_facts_to_legacy(ixbrl_facts_by_period)
                legacy_data["profile"]["symbol"] = ticker.upper()
                
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
                    valuation_ratios=quant_results.get("valuation_ratios", {}),
                    accounting_corrections=quant_results.get("accounting_corrections", []),
                    input_provenance=quant_results.get("input_provenance", {}),
                    findings=[f"[FILE SOURCED] {f}" for f in quant_results.get("quantitative_findings", [])]
                )
            else:
                # NO API FALLBACK - Single source of truth: file only
                logger.info("no_ixbrl_found_file_only_mode", ticker=ticker)
                report.quantitative_audit.findings = [
                    "No iXBRL data found in filing. This is common for older filings (pre-2020).",
                    "Quantitative analysis limited to AI textual scan."
                ]

            # Generate Execution Risk Matrix using file data only (no external API)
            if extractor:
                try:
                    from app.services.sensitivity_calculator import SensitivityCalculator
                    # Use standard WACC assumption for file-only mode (KISS)
                    wacc = 0.10  # Standard 10% discount rate
                    
                    # Calculate from file data where available
                    try:
                        risk_free = 0.045  # Standard assumption
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
                        logger.debug("wacc_calculation_failed_for_matrix_using_default", error=str(e))
                    
                    # Build matrix from file data
                    # SensitivityCalculator requires projected FCFs, not base FCF
                    base_fcf = extractor.free_cash_flow() or 0
                    base_growth = extractor.revenue_cagr() or 0.05
                    projection_years = 5
                    terminal_growth = 0.025
                    
                    # Project FCFs for the required periods (simple growth model)
                    projected_fcfs = []
                    current_fcf = base_fcf
                    for year in range(projection_years):
                        current_fcf = current_fcf * (1 + base_growth)
                        projected_fcfs.append(current_fcf)
                    
                    sens_calc = SensitivityCalculator(
                        projected_fcfs=projected_fcfs,
                        projection_years=projection_years,
                        shares_outstanding=extractor.shares_outstanding() or 1,
                        total_debt=extractor.total_debt() or 0,
                        cash=extractor.cash() or 0
                    )
                    
                    # Standard margin/growth steps for execution risk matrix
                    margin_steps = [-0.05, -0.025, 0, 0.025, 0.05]
                    growth_steps = [-0.05, -0.025, 0, 0.025, 0.05]
                    
                    matrix = sens_calc.generate_margin_growth_matrix(
                        base_revenue=extractor.latest_revenue() or 1,
                        base_margin=extractor.operating_margin() or 0.15,
                        base_growth=base_growth,
                        discount_rate=wacc,
                        terminal_growth=terminal_growth,
                        margin_steps=margin_steps,
                        growth_steps=growth_steps
                    )
                    report.quantitative_audit.margin_growth_sensitivity = matrix
                except Exception as e:
                    logger.warning("matrix_generation_failed", ticker=ticker, error=str(e))
            
        except Exception as e:
            logger.warning("quantitative_audit_failed", ticker=ticker, error=str(e))
            # Don't fail the whole audit if numerical data is missing
        
        # 3. PERSISTENCE: Save to DB if accession_number is provided
        if accession_number:
            repo = get_filings_repository()
            await repo.update_forensic_report(
                accession_number=accession_number,
                consistency_score=report.accounting_consistency_score,
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
    accession_number: Optional[str] = Query(None, description="SEC accession number for persistence"),
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
        
        # Save granular sections for forensic persistence
        if accession_number:
            asyncio.create_task(sec_filings_service.save_filing_sections(accession_number, html_content))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch filing: {str(e)}")

    # 2. Fast Quantitative Audit (SINGLE SOURCE OF TRUTH: FILE ONLY - NO API CALLS)
    quant_audit = QuantitativeAudit(sloan_ratio=None, altman_z_score=None, beneish_m_score=None, findings=[])
    try:
        from app.services.data_adapter import ixbrl_facts_to_legacy
        ixbrl_facts = parser.extract_ixbrl_facts(html_content)
        
        # LTM Data Merging (NOTES2.md Item #8)
        if ixbrl_facts:
            ixbrl_facts = await _get_ltm_facts_if_needed(ticker, ixbrl_facts, document_url)
        
        if ixbrl_facts:
            legacy_data = ixbrl_facts_to_legacy(ixbrl_facts)
            legacy_data["profile"]["symbol"] = ticker.upper()

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
                valuation_ratios=quant_results.get("valuation_ratios", {}),
                accounting_corrections=quant_results.get("accounting_corrections", []),
                input_provenance=quant_results.get("input_provenance", {}),
                findings=[f"[FILE SOURCED] {f}" for f in quant_results.get("quantitative_findings", [])]
            )
        else:
            # NO API FALLBACK - Single source of truth
            logger.info("no_ixbrl_found_file_only_mode", ticker=ticker)
            quant_audit.findings = [
                "No iXBRL data found in filing. This is common for older filings (pre-2020).",
                "Quantitative analysis limited to AI textual scan."
            ]
    except Exception as e:
        logger.warning("scan_quantitative_audit_failed", ticker=ticker, error=str(e))

    # 3. Textual Forensic Scan (LLM) - Clean HTML to save tokens/prevent TPM limit
    try:
        clean_text = parser.clean_html(html_content)
        if query:
            result = await analyzer.analyze(clean_text, query)
        else:
            result = await analyzer.extract_red_flags(clean_text)
            
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