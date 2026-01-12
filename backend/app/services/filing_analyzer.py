"""SEC Filing Analyzer using Google Gemini (Free Tier).

Phase 2: Analyze SEC filings with LLM-powered forensic analysis.
Uses Gemini 2.0 Flash - free tier with 1M token context window.

Free tier limits:
- 15 requests per minute
- 1,500 requests per day  
- 1 million tokens per day
"""
import asyncio
import os
import re
import time
import structlog
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from google import genai
from google.genai import types

from app.services.rate_limiter_sqlite import rate_limiter
from app.services.telemetry_repository import get_telemetry_repository
from app.services.logging_config import logger # Use structlog logger
from app.services.resilience import get_circuit_breaker
from app.schemas.forensic import ForensicReport


# Institutional Forensic Prompt Suite
FORENSIC_PROMPT_SUITE = {
    "accounting_forensics": """
    Analyze the financial statements for high-risk accrual accounting:
    1. Sloan Ratio: Is Net Income significantly higher than Cash Flow from Operations? 
    2. Capitalization Creep: Compare 'Other Assets' and 'Intangibles' growth. Is management hiding expenses in the balance sheet?
    3. Revenue Recognition: Look for changes in wording (e.g., shifts to 'percentage of completion').
    """,
    "inventory_sales_divergence": """
    Compare Inventory growth to Revenue growth.
    - If Inventory > Revenue growth by >20%, explain the risk of obsolescence or 'channel stuffing'.
    - If Inventory is falling while Revenue is growing, is it efficiency or a supply chain risk?
    """,
    "textual_alpha": """
    Analyze the MD&A (Management Discussion & Analysis) for psychological red flags:
    1. Tone Shifts: Compare to previous year if available. Is language becoming more legalistic/passive?
    2. Risk Factor Changes: Identify new or significantly expanded risk disclosures.
    3. Vague Language: Flag evasive answers regarding liquidity or competitive pressures.
    """,
    "auditor_skepticism": """
    Analyze the Auditor's Report (Item 8 or separate section):
    1. Critical Audit Matters (CAMs): Identify highlighted risks (e.g., 'Revenue Recognition', 'Inventory Valuation'). 
    2. Auditor Tenure: How long has the firm been auditing? (Flag if > 20 years - risk of capture).
    3. Audit Firm Quality: Is it a Big 4 firm? (Flag if small/unknown firm for a multi-billion cap).
    """
}


class AnalyzerError(Exception):
    """Error during filing analysis."""
    pass


class RateLimitError(AnalyzerError):
    """Rate limit exceeded - retry later."""
    def __init__(self, retry_after: float = 60.0):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


@dataclass
class AnalysisResult:
    """Result of filing analysis."""
    query: str
    response: str
    model: str
    tokens_used: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class FilingAnalyzer:
    """
    Analyze SEC filings using Google Gemini.
    
    Free tier limits (as of 2026):
    - 15 requests per minute
    - 1,500 requests per day  
    - 1 million tokens per day
    - 1 million token context window (can fit entire 10-K!)
    
    Usage:
        analyzer = FilingAnalyzer()
        result = await analyzer.analyze(
            filing_text="...",
            query="What changed in revenue recognition?"
        )
    """
    
    MODEL = "gemini-2.5-flash"  # Best free model with 1M context
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise AnalyzerError("GEMINI_API_KEY not set in environment")
        
        self.client = genai.Client(api_key=self.api_key)
        self._provider_name = "gemini"
    
    async def _check_rate_limit(self):
        """Ensure we don't exceed rate limits using central SQLite rate limiter."""
        if await rate_limiter.is_at_limit(self._provider_name):
            wait_time = await rate_limiter.get_time_until_reset(self._provider_name) or 60
            raise RateLimitError(retry_after=wait_time)
        
        await rate_limiter.record_call(self._provider_name)
    
    async def analyze(
        self,
        filing_text: str,
        query: str,
        system_prompt: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze a filing section with a specific query (Async).
        Wrapped in a circuit breaker to prevent cascading failures.
        """
        breaker = get_circuit_breaker(self._provider_name)
        try:
            return await breaker.call(
                self._analyze_internal,
                filing_text,
                query,
                system_prompt
            )
        except Exception as e:
            # Re-raise known errors, wrap others
            if isinstance(e, (RateLimitError, AnalyzerError)):
                raise e
            raise AnalyzerError(f"Analysis engine failure: {str(e)}")

    async def _analyze_internal(
        self,
        filing_text: str,
        query: str,
        system_prompt: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Internal implementation of analysis.
        """
        await self._check_rate_limit()
        
        default_system = """You are an expert forensic accountant analyzing SEC filings.
Your job is to identify:
- Accounting policy changes
- Revenue recognition issues  
- Related party transactions
- Risk factors and red flags
- Management tone shifts

Be specific. Quote relevant passages. Flag anything suspicious."""

        prompt = f"""{system_prompt or default_system}

=== SEC FILING TEXT ===
{filing_text}
=== END FILING ===

ANALYSIS REQUEST: {query}

Provide a detailed, specific analysis with evidence from the filing."""

        start_time = time.time()
        telemetry_repo = get_telemetry_repository()
        # Attempt to get trace_id from current context
        trace_id = structlog.contextvars.get_contextvars().get("trace_id", "unknown")

        try:
            # P0 Bug Fix: Use asynchronous client to avoid blocking the event loop
            response = await self.client.aio.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,  # Low temp for factual analysis
                    max_output_tokens=4096,
                ),
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Record telemetry
            await telemetry_repo.record_metric(
                trace_id=trace_id,
                operation="gemini_analysis",
                duration_ms=duration_ms,
                status="success"
            )

            logger.info(
                "gemini_analysis_completed",
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id
            )
            
            return AnalysisResult(
                query=query,
                response=response.text,
                model=self.MODEL,
                tokens_used=None,
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_str = str(e)
            
            # Record failed telemetry
            await telemetry_repo.record_metric(
                trace_id=trace_id,
                operation="gemini_analysis",
                duration_ms=duration_ms,
                status="failed",
                error_message=error_str
            )

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Extract retry time if available
                match = re.search(r'retry in (\d+\.?\d*)s', error_str.lower())
                retry_after = float(match.group(1)) if match else 60.0
                raise RateLimitError(retry_after=retry_after)
            
            logger.error(f"Analysis failed: {e}")
            raise AnalyzerError(f"Analysis failed: {e}")
    
    async def compare_filings(
        self,
        current_filing: str,
        previous_filing: str,
        section: str = "entire filing",
    ) -> AnalysisResult:
        """
        Compare two filings to identify changes (Async).
        
        Args:
            current_filing: This year's filing text
            previous_filing: Last year's filing text
            section: Which section to focus on (e.g., "Note 7", "MD&A")
        """
        query = f"""Compare the {section} between these two filings.

CURRENT YEAR FILING:
{current_filing[:400000]}  

PREVIOUS YEAR FILING:
{previous_filing[:400000]}

Identify:
1. Material changes in accounting policies or estimates
2. New or significantly expanded risk disclosures
3. Shifts in management tone (becoming more defensive/legalistic)
4. Removed language that was previously positive
5. Any forensic red flags regarding revenue or liabilities

Highlight specific wording changes that indicate a shift in economic reality."""

        return await self.analyze(
            filing_text="",  # Text is in query
            query=query,
            system_prompt="You are an expert forensic accountant comparing two SEC filings year-over-year. Focus on material changes and linguistic shifts.",
        )
    
    async def extract_red_flags(self, filing_text: str) -> AnalysisResult:
        """Quick scan for common accounting red flags using FORENSIC_PROMPT_SUITE (Async)."""
        combined_query = "\n".join([f"SECTION {k.upper()}:\n{v}" for k, v in FORENSIC_PROMPT_SUITE.items()])
        
        return await self.analyze(
            filing_text=filing_text,
            query=f"""Scan this filing for institutional-grade red flags:

{combined_query}

For each red flag found, quote the relevant text and explain the economic risk to a long-term investor."""
        )

    async def analyze_forensic(self, filing_text: str) -> ForensicReport:
        """
        Run a deep forensic scan and return a structured report (Async).
        """
        await self._check_rate_limit()
        
        system_prompt = """You are a senior forensic accountant at a Tier-1 hedge fund.
Your task is to analyze the provided SEC filing for accounting shenanigans and financial risk.
You must output your findings in a strict JSON format matching the requested schema.

Evaluate these categories:
1. Revenue: Recognition shifts, aggressive accruals, channel stuffing.
2. Expenses: Capitalization creep (hiding expenses in assets), under-reserving.
3. Assets: Inventory/Sales divergence, goodwill impairment risk, 'Other Assets' bloat.
4. Liabilities: Unrecorded obligations, 'Cookie Jar' reserves, off-balance sheet items.
5. Cash Flow: Divergence from Net Income, unsustainable financing.
6. Disclosures: Vague language in MD&A, removal of previously positive statements.
7. Management: Tone shifts, risk factor bloat, executive turnover mentions.
8. Auditor: Critical Audit Matters (CAMs), auditor tenure (>20 years is high risk), firm quality.

Critical Tasks:
- Assign a score from 1 (Safe) to 10 (High Danger) for each category.
- Calculate an overall 'Accounting Consistency Score' from 1 to 100 (100 = most consistent/clean).
- Identify the 'Reported EPS' (Basic or Diluted) from the filing.
- Propose specific 'EPS Adjustments' to reach a 'Forensic EPS' that reflects economic reality. 
  For example, if they capitalized $100M of R&D that should have been expensed, subtract that from net income / shares.
  If they had a one-time gain on asset sale, subtract that.
  If they are under-reserving for bad debt, estimate the impact and subtract it."""

        query = "Perform a complete institutional-grade forensic audit of this filing."

        prompt = f"""{system_prompt}

=== SEC FILING TEXT ===
{filing_text[:500000]}
=== END FILING ===

{query}"""

        start_time = time.time()
        telemetry_repo = get_telemetry_repository()
        trace_id = structlog.contextvars.get_contextvars().get("trace_id", "unknown")

        try:
            # Use the new GenerateContentConfig with response_mime_type and response_schema
            response = await self.client.aio.models.generate_content(
                model=self.MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=ForensicReport,
                ),
            )
            
            duration_ms = (time.time() - start_time) * 1000
            await telemetry_repo.record_metric(
                trace_id=trace_id,
                operation="gemini_forensic_analysis",
                duration_ms=duration_ms,
                status="success"
            )

            # The response.parsed should contain the model instance if response_schema was used
            report = response.parsed
            if not isinstance(report, ForensicReport):
                # Fallback if parsing didn't return the model
                report = ForensicReport.model_validate_json(response.text)
            
            report.model = self.MODEL
            return report
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            await telemetry_repo.record_metric(
                trace_id=trace_id,
                operation="gemini_forensic_analysis",
                duration_ms=duration_ms,
                status="failed",
                error_message=str(e)
            )
            logger.error(f"Forensic analysis failed: {e}")
            raise AnalyzerError(f"Forensic analysis failed: {e}")


# Singleton instance
_analyzer: Optional[FilingAnalyzer] = None


def get_filing_analyzer() -> FilingAnalyzer:
    """Get or create the filing analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FilingAnalyzer()
    return _analyzer
