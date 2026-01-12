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
from typing import Optional, List

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


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
        self._request_times: List[float] = []
        self._max_rpm = 14  # Stay under 15 RPM limit
    
    def _check_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        import time
        now = time.time()
        
        # Remove requests older than 1 minute
        self._request_times = [t for t in self._request_times if now - t < 60]
        
        if len(self._request_times) >= self._max_rpm:
            wait_time = 60 - (now - self._request_times[0])
            raise RateLimitError(retry_after=wait_time)
        
        self._request_times.append(now)
    
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
        """Quick scan for common accounting red flags."""
        return self.analyze(
            filing_text=filing_text,
            query="""Scan this filing for red flags:

1. Revenue recognition changes or aggressive policies
2. Related party transactions
3. Off-balance sheet arrangements
4. Unusual inventory or receivables growth
5. Changes in auditor or audit opinions
6. Going concern language
7. Material weakness in internal controls
8. Significant estimate changes
9. Non-GAAP metrics that differ greatly from GAAP
10. Vague or evasive language in MD&A

For each red flag found, quote the relevant text and explain why it's concerning."""
        )


# Singleton instance
_analyzer: Optional[FilingAnalyzer] = None


def get_filing_analyzer() -> FilingAnalyzer:
    """Get or create the filing analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FilingAnalyzer()
    return _analyzer
