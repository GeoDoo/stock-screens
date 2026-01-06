"""
Dividend Analyzer Service

Analyzes dividend history, growth, and yield metrics.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from collections import defaultdict


@dataclass
class DividendPayment:
    """A single dividend payment."""
    date: str
    amount: float


@dataclass
class DividendHistory:
    """Complete dividend analysis result."""
    has_dividends: bool
    current_annual_dividend: Optional[float] = None
    current_yield: Optional[float] = None
    payout_ratio: Optional[float] = None  # Dividends / Net Income
    dividend_cagr: Optional[float] = None
    consecutive_years: int = 0
    annual_dividends: Dict[int, float] = field(default_factory=dict)
    payments: List[DividendPayment] = field(default_factory=list)
    average_yield_5yr: Optional[float] = None


class DividendAnalyzer:
    """
    Analyzes dividend history and calculates key metrics.
    
    Metrics:
    - Current annual dividend (sum of last 4 quarters)
    - Current dividend yield
    - 5-year dividend CAGR
    - Consecutive years of dividend payments
    - Annual dividend totals
    """
    
    def analyze(
        self,
        payments: List[DividendPayment],
        current_price: Optional[float],
        shares_outstanding: Optional[float],
        net_income: Optional[float] = None,
    ) -> DividendHistory:
        """
        Analyze dividend history.
        
        Args:
            payments: List of historical dividend payments
            current_price: Current stock price (for yield calculation)
            shares_outstanding: Number of shares (for per-share calculations)
            net_income: Annual net income (for payout ratio calculation)
            
        Returns:
            DividendHistory with all calculated metrics
        """
        if not payments:
            return DividendHistory(
                has_dividends=False,
                consecutive_years=0,
            )
        
        # Sort payments by date (oldest first)
        sorted_payments = sorted(
            payments, 
            key=lambda p: p.date
        )
        
        # Group by year
        annual_dividends = self._calculate_annual_totals(sorted_payments)
        
        # Calculate current annual dividend (trailing 12 months)
        current_annual = self._calculate_trailing_annual(sorted_payments)
        
        # Calculate yield
        current_yield = None
        if current_price and current_price > 0 and current_annual:
            current_yield = current_annual / current_price
        
        # Calculate payout ratio (total dividends / net income)
        payout_ratio = None
        if net_income and net_income > 0 and current_annual and shares_outstanding:
            # current_annual is per-share, multiply by shares to get total
            total_dividends = current_annual * shares_outstanding
            payout_ratio = total_dividends / net_income
        
        # Calculate CAGR
        dividend_cagr = self._calculate_cagr(annual_dividends)
        
        # Count consecutive years
        consecutive_years = self._count_consecutive_years(annual_dividends)
        
        return DividendHistory(
            has_dividends=True,
            current_annual_dividend=current_annual,
            current_yield=current_yield,
            payout_ratio=payout_ratio,
            dividend_cagr=dividend_cagr,
            consecutive_years=consecutive_years,
            annual_dividends=annual_dividends,
            payments=sorted_payments,
        )
    
    def _calculate_annual_totals(
        self, 
        payments: List[DividendPayment]
    ) -> Dict[int, float]:
        """Calculate total dividends paid each year."""
        annual = defaultdict(float)
        
        for payment in payments:
            try:
                year = datetime.strptime(payment.date[:10], "%Y-%m-%d").year
                annual[year] += payment.amount
            except (ValueError, TypeError):
                continue
        
        return dict(annual)
    
    def _calculate_trailing_annual(
        self, 
        payments: List[DividendPayment]
    ) -> Optional[float]:
        """Calculate trailing 12-month dividend total."""
        if not payments:
            return None
        
        # Get payments from the last 12 months
        now = datetime.now()
        one_year_ago = datetime(now.year - 1, now.month, now.day)
        
        trailing_total = 0.0
        for payment in payments:
            try:
                payment_date = datetime.strptime(payment.date[:10], "%Y-%m-%d")
                if payment_date >= one_year_ago:
                    trailing_total += payment.amount
            except (ValueError, TypeError):
                continue
        
        # If no recent payments, estimate from most recent year
        if trailing_total == 0:
            annual = self._calculate_annual_totals(payments)
            if annual:
                most_recent_year = max(annual.keys())
                return annual[most_recent_year]
        
        return trailing_total if trailing_total > 0 else None
    
    def _calculate_cagr(
        self, 
        annual_dividends: Dict[int, float]
    ) -> Optional[float]:
        """Calculate compound annual growth rate of dividends."""
        if len(annual_dividends) < 2:
            return None
        
        years = sorted(annual_dividends.keys())
        
        # Need at least 2 years with dividends
        start_year = years[0]
        end_year = years[-1]
        
        start_dividend = annual_dividends[start_year]
        end_dividend = annual_dividends[end_year]
        
        if start_dividend <= 0 or end_dividend <= 0:
            return None
        
        num_years = end_year - start_year
        if num_years <= 0:
            return None
        
        # CAGR formula: (end/start)^(1/years) - 1
        cagr = (end_dividend / start_dividend) ** (1 / num_years) - 1
        
        return cagr
    
    def _count_consecutive_years(
        self, 
        annual_dividends: Dict[int, float]
    ) -> int:
        """Count consecutive years of dividend payments from most recent."""
        if not annual_dividends:
            return 0
        
        years = sorted(annual_dividends.keys(), reverse=True)
        
        if not years:
            return 0
        
        # Start from the most recent year with dividends
        consecutive = 1
        expected_year = years[0] - 1
        
        for year in years[1:]:
            if year == expected_year:
                consecutive += 1
                expected_year -= 1
            else:
                break
        
        return consecutive

