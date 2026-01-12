"""SEC Filing Analyzer using Google Gemini (Free Tier).

Phase 2: Analyze SEC filings with LLM-powered forensic analysis.
Uses Gemini 2.0 Flash - free tier with 1M token context window.

Free tier limits:
- 15 requests per minute
- 1,500 requests per day  
- 1 million tokens per day
"""
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict

from google import genai
from google.genai import types

from app.services.rate_limiter_sqlite import rate_limiter

logger = logging.getLogger(__name__)


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
            self.timestamp = datetime.utcnow()


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
    
    def _check_rate_limit(self):
        """Ensure we don't exceed rate limits using central SQLite rate limiter."""
        if rate_limiter.is_at_limit(self._provider_name):
            wait_time = rate_limiter.get_time_until_reset(self._provider_name) or 60
            raise RateLimitError(retry_after=wait_time)
        
        rate_limiter.record_call(self._provider_name)
    
    def analyze(
        self,
        filing_text: str,
        query: str,
        system_prompt: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze a filing section with a specific query.
        
        Args:
            filing_text: The SEC filing text (can be very long - 1M context)
            query: What to analyze (e.g., "List all related party transactions")
            system_prompt: Optional custom system prompt
            
        Returns:
            AnalysisResult with the response
            
        Raises:
            RateLimitError: If rate limit would be exceeded
            AnalyzerError: For other errors
        """
        self._check_rate_limit()
        
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

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,  # Low temp for factual analysis
                    max_output_tokens=4096,
                ),
            )
            
            return AnalysisResult(
                query=query,
                response=response.text,
                model=self.MODEL,
                tokens_used=None,  # Token counting requires additional API call
            )
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Extract retry time if available
                match = re.search(r'retry in (\d+\.?\d*)s', error_str.lower())
                retry_after = float(match.group(1)) if match else 60.0
                raise RateLimitError(retry_after=retry_after)
            
            logger.error(f"Analysis failed: {e}")
            raise AnalyzerError(f"Analysis failed: {e}")
    
    def compare_filings(
        self,
        current_filing: str,
        previous_filing: str,
        section: str = "entire filing",
    ) -> AnalysisResult:
        """
        Compare two filings to identify changes.
        
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
1. Material changes in accounting policies
2. New risk disclosures
3. Changes in management tone
4. Removed or added language
5. Any red flags"""

        return self.analyze(
            filing_text="",  # Text is in query
            query=query,
            system_prompt="You are comparing two SEC filings year-over-year. Focus on material changes.",
        )
    
    def extract_red_flags(self, filing_text: str) -> AnalysisResult:
        """Quick scan for common accounting red flags using FORENSIC_PROMPT_SUITE."""
        combined_query = "\n".join([f"SECTION {k.upper()}:\n{v}" for k, v in FORENSIC_PROMPT_SUITE.items()])
        
        return self.analyze(
            filing_text=filing_text,
            query=f"""Scan this filing for institutional-grade red flags:

{combined_query}

For each red flag found, quote the relevant text and explain the economic risk to a long-term investor."""
        )


# Singleton instance
_analyzer: Optional[FilingAnalyzer] = None


def get_filing_analyzer() -> FilingAnalyzer:
    """Get or create the filing analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FilingAnalyzer()
    return _analyzer
