"""
Valuation service implementing multiple intrinsic value calculation methods.

Methods:
    - Graham's formula (value investing classic)
    - DCF (Discounted Cash Flow)
    - Asset-based (NAV/Book Value)
    - EPV (Earnings Power Value)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import logging

from app.models.stock import Stock
from app.models.valuation import (
    GrahamValuation,
    DCFValuation,
    AssetBasedValuation,
    EPVValuation,
    MarginOfSafety,
    ValuationResult,
    ValuationMethod,
)

logger = logging.getLogger(__name__)


class ValuationService:
    """Service for calculating stock intrinsic values."""

    # Graham constants
    GRAHAM_BASE_PE = Decimal("8.5")
    GRAHAM_1962_YIELD = Decimal("4.4")  # As percentage
    GRAHAM_MAX_GROWTH = Decimal("0.15")  # Cap growth at 15%

    # Default assumptions
    DEFAULT_AAA_YIELD = Decimal("0.05")
    DEFAULT_DISCOUNT_RATE = Decimal("0.10")
    DEFAULT_TERMINAL_GROWTH = Decimal("0.025")
    DEFAULT_TAX_RATE = Decimal("0.25")

    def _round(self, value: Decimal, places: int = 2) -> Decimal:
        """Round decimal to specified places."""
        return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)

    def graham_valuation(
        self,
        eps: Decimal,
        growth_rate: Decimal,
        aaa_yield: Optional[Decimal] = None,
    ) -> Optional[GrahamValuation]:
        """
        Calculate intrinsic value using Graham's formula.

        Formula: V = EPS × (8.5 + 2g) × 4.4 / Y
        
        Where:
            - EPS = Earnings per share
            - g = Expected growth rate (as percentage, e.g., 7 for 7%)
            - 4.4 = Average yield of AAA bonds in 1962
            - Y = Current AAA bond yield (as percentage)

        Args:
            eps: Earnings per share (TTM)
            growth_rate: Expected annual growth rate (as decimal, e.g., 0.07)
            aaa_yield: Current AAA corporate bond yield (as decimal, e.g., 0.05)

        Returns:
            GrahamValuation with calculated intrinsic value, or None if invalid inputs
        """
        if eps <= 0:
            logger.debug("Graham valuation: negative EPS, returning None")
            return None

        if aaa_yield is None:
            aaa_yield = self.DEFAULT_AAA_YIELD

        if aaa_yield <= 0:
            logger.warning("Graham valuation: invalid AAA yield")
            return None

        # Cap unrealistic growth rates
        capped_growth = min(growth_rate, self.GRAHAM_MAX_GROWTH)
        
        # Convert growth to percentage for formula (0.07 -> 7)
        growth_pct = capped_growth * 100
        yield_pct = aaa_yield * 100

        # Graham formula: V = EPS × (8.5 + 2g) × 4.4 / Y
        multiplier = self.GRAHAM_BASE_PE + (Decimal("2") * growth_pct)
        yield_adjustment = self.GRAHAM_1962_YIELD / yield_pct
        intrinsic_value = eps * multiplier * yield_adjustment

        return GrahamValuation(
            eps=eps,
            growth_rate=capped_growth,
            aaa_yield=aaa_yield,
            intrinsic_value=self._round(intrinsic_value),
        )

    def dcf_valuation(
        self,
        fcf_current: Decimal,
        growth_rate_high: Decimal,
        growth_rate_terminal: Decimal,
        high_growth_years: int,
        discount_rate: Decimal,
        shares_outstanding: int,
    ) -> Optional[DCFValuation]:
        """
        Calculate intrinsic value using Discounted Cash Flow.

        Projects future free cash flows at high growth rate, then applies
        terminal value using perpetual growth formula.

        Args:
            fcf_current: Current free cash flow
            growth_rate_high: Growth rate during high-growth period
            growth_rate_terminal: Perpetual growth rate after high-growth period
            high_growth_years: Number of years of high growth
            discount_rate: WACC or required return rate
            shares_outstanding: Number of shares outstanding

        Returns:
            DCFValuation with projected FCFs and intrinsic value per share
        """
        if fcf_current <= 0:
            logger.debug("DCF valuation: negative FCF, returning None")
            return None

        if growth_rate_terminal >= discount_rate:
            logger.warning(
                "DCF valuation: terminal growth >= discount rate, invalid"
            )
            return None

        if shares_outstanding <= 0:
            return None

        # Project future FCFs
        projected_fcfs: list[Decimal] = []
        fcf = fcf_current
        
        for year in range(1, high_growth_years + 1):
            fcf = fcf * (1 + growth_rate_high)
            projected_fcfs.append(self._round(fcf, 0))

        # Calculate terminal value (Gordon Growth Model)
        # TV = FCF_n+1 / (r - g)
        fcf_terminal = fcf * (1 + growth_rate_terminal)
        terminal_value = fcf_terminal / (discount_rate - growth_rate_terminal)

        # Discount all cash flows to present value
        total_pv = Decimal("0")
        
        for year, projected_fcf in enumerate(projected_fcfs, 1):
            discount_factor = (1 + discount_rate) ** year
            pv = projected_fcf / discount_factor
            total_pv += pv

        # Discount terminal value
        terminal_discount_factor = (1 + discount_rate) ** high_growth_years
        terminal_pv = terminal_value / terminal_discount_factor
        total_pv += terminal_pv

        # Calculate per share value
        intrinsic_value_per_share = total_pv / shares_outstanding

        return DCFValuation(
            fcf_current=fcf_current,
            growth_rate_high=growth_rate_high,
            growth_rate_terminal=growth_rate_terminal,
            high_growth_years=high_growth_years,
            discount_rate=discount_rate,
            shares_outstanding=shares_outstanding,
            projected_fcfs=projected_fcfs,
            terminal_value=self._round(terminal_value, 0),
            total_present_value=self._round(total_pv, 0),
            intrinsic_value_per_share=self._round(intrinsic_value_per_share),
        )

    def asset_based_valuation(
        self,
        total_assets: Decimal,
        total_liabilities: Decimal,
        intangible_assets: Decimal,
        shares_outstanding: int,
        asset_discount: Decimal = Decimal("0"),
    ) -> Optional[AssetBasedValuation]:
        """
        Calculate intrinsic value using asset-based approach.

        NAV = Total Assets - Total Liabilities
        Tangible Book Value = NAV - Intangible Assets

        Args:
            total_assets: Total assets from balance sheet
            total_liabilities: Total liabilities from balance sheet
            intangible_assets: Intangible assets (goodwill, patents, etc.)
            shares_outstanding: Number of shares outstanding
            asset_discount: Optional discount to apply to assets (0-1)

        Returns:
            AssetBasedValuation with NAV and tangible book value per share
        """
        if shares_outstanding <= 0:
            return None

        # Apply asset discount if specified
        adjusted_assets = total_assets * (1 - asset_discount)

        # Calculate NAV
        nav = adjusted_assets - total_liabilities
        nav_per_share = nav / shares_outstanding

        # Calculate Tangible Book Value
        tbv = adjusted_assets - intangible_assets - total_liabilities
        tbv_per_share = tbv / shares_outstanding

        return AssetBasedValuation(
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            intangible_assets=intangible_assets,
            shares_outstanding=shares_outstanding,
            asset_discount=asset_discount,
            net_asset_value=self._round(nav, 0),
            tangible_book_value=self._round(tbv, 0),
            nav_per_share=self._round(nav_per_share),
            tbv_per_share=self._round(tbv_per_share),
        )

    def epv_valuation(
        self,
        ebit: Decimal,
        tax_rate: Decimal,
        maintenance_capex: Decimal,
        cost_of_capital: Decimal,
        shares_outstanding: int,
        excess_cash: Decimal = Decimal("0"),
        total_debt: Decimal = Decimal("0"),
    ) -> Optional[EPVValuation]:
        """
        Calculate Earnings Power Value (Greenwald method).

        EPV assumes no growth and values the company based on
        sustainable/normalized earnings.

        EPV = Normalized Earnings / Cost of Capital

        Args:
            ebit: Earnings before interest and taxes
            tax_rate: Effective tax rate (0-1)
            maintenance_capex: Maintenance CapEx (not growth CapEx)
            cost_of_capital: WACC or cost of equity
            shares_outstanding: Number of shares outstanding
            excess_cash: Cash beyond operating needs
            total_debt: Total debt to subtract from enterprise value

        Returns:
            EPVValuation with EPV per share
        """
        if ebit <= 0:
            logger.debug("EPV valuation: negative EBIT, returning None")
            return None

        if cost_of_capital <= 0 or shares_outstanding <= 0:
            return None

        # Calculate normalized earnings
        after_tax_ebit = ebit * (1 - tax_rate)
        normalized_earnings = after_tax_ebit - maintenance_capex

        if normalized_earnings <= 0:
            return None

        # EPV of operations
        epv_operations = normalized_earnings / cost_of_capital

        # Adjust for balance sheet items to get equity value
        epv_equity = epv_operations + excess_cash - total_debt

        # Per share
        epv_per_share = epv_equity / shares_outstanding

        return EPVValuation(
            ebit=ebit,
            tax_rate=tax_rate,
            maintenance_capex=maintenance_capex,
            cost_of_capital=cost_of_capital,
            shares_outstanding=shares_outstanding,
            excess_cash=excess_cash,
            total_debt=total_debt,
            normalized_earnings=self._round(normalized_earnings, 0),
            epv_operations=self._round(epv_operations, 0),
            epv_equity=self._round(epv_equity, 0),
            epv_per_share=self._round(epv_per_share),
        )

    def calculate_margin_of_safety(
        self,
        current_price: Decimal,
        intrinsic_value: Decimal,
        min_margin_required: Decimal = Decimal("0.25"),
    ) -> MarginOfSafety:
        """
        Calculate margin of safety.

        Margin of Safety = (Intrinsic Value - Price) / Intrinsic Value

        Args:
            current_price: Current stock price
            intrinsic_value: Calculated intrinsic value
            min_margin_required: Minimum margin to consider stock undervalued

        Returns:
            MarginOfSafety with percentage and buy signal
        """
        margin_decimal = (intrinsic_value - current_price) / intrinsic_value
        margin_percent = self._round(margin_decimal * 100)

        # Stock is undervalued if margin >= required threshold
        is_undervalued = margin_decimal >= min_margin_required

        return MarginOfSafety(
            current_price=current_price,
            intrinsic_value=intrinsic_value,
            margin_of_safety=margin_percent,
            is_undervalued=is_undervalued,
            min_margin_required=min_margin_required,
        )

    def _determine_primary_method(self, stock: Stock) -> ValuationMethod:
        """
        Determine the most appropriate valuation method for a stock.

        - Financials/Banks -> Asset-based
        - Stable, mature companies -> EPV
        - Growth companies -> DCF
        - General value stocks -> Graham
        """
        sector = (stock.sector or "").lower()
        fundamentals = stock.fundamentals

        # Financial sector -> Asset-based
        if "financial" in sector or "bank" in sector or "insurance" in sector:
            return ValuationMethod.ASSET_BASED

        if fundamentals:
            # High growth -> DCF
            growth = fundamentals.revenue_growth or Decimal("0")
            if growth > Decimal("15"):
                return ValuationMethod.DCF

            # Stable earnings, low growth -> EPV
            if Decimal("0") <= growth <= Decimal("5"):
                return ValuationMethod.EPV

        # Default to Graham
        return ValuationMethod.GRAHAM

    def calculate_full_valuation(self, stock: Stock) -> ValuationResult:
        """
        Calculate comprehensive valuation using all applicable methods.

        Args:
            stock: Stock with fundamentals data

        Returns:
            ValuationResult with all valuations and composite metrics
        """
        warnings: list[str] = []
        methods_used: list[ValuationMethod] = []
        intrinsic_values: list[Decimal] = []

        current_price = Decimal("0")
        if stock.price:
            current_price = stock.price.current

        fundamentals = stock.fundamentals
        if not fundamentals:
            warnings.append("No fundamental data available")
            return ValuationResult(
                symbol=stock.symbol,
                current_price=current_price,
                warnings=warnings,
            )

        # Graham valuation
        graham_result = None
        if fundamentals.eps and fundamentals.eps > 0:
            growth = fundamentals.eps_growth_5y or Decimal("0.05")
            graham_result = self.graham_valuation(
                eps=fundamentals.eps,
                growth_rate=growth / 100 if growth > 1 else growth,
            )
            if graham_result and graham_result.intrinsic_value:
                methods_used.append(ValuationMethod.GRAHAM)
                intrinsic_values.append(graham_result.intrinsic_value)
        else:
            warnings.append("Graham: No positive EPS available")

        # DCF valuation
        dcf_result = None
        if fundamentals.fcf_per_share and fundamentals.shares_outstanding:
            fcf_total = fundamentals.fcf_per_share * fundamentals.shares_outstanding
            if fcf_total > 0:
                growth = fundamentals.revenue_growth or Decimal("5")
                growth_rate = growth / 100 if growth > 1 else growth
                dcf_result = self.dcf_valuation(
                    fcf_current=fcf_total,
                    growth_rate_high=min(growth_rate, Decimal("0.20")),
                    growth_rate_terminal=self.DEFAULT_TERMINAL_GROWTH,
                    high_growth_years=5,
                    discount_rate=self.DEFAULT_DISCOUNT_RATE,
                    shares_outstanding=fundamentals.shares_outstanding,
                )
                if dcf_result and dcf_result.intrinsic_value_per_share:
                    methods_used.append(ValuationMethod.DCF)
                    intrinsic_values.append(dcf_result.intrinsic_value_per_share)
        else:
            warnings.append("DCF: No FCF or shares outstanding data")

        # Asset-based valuation
        asset_result = None
        if fundamentals.book_value_per_share and fundamentals.shares_outstanding:
            # Estimate assets/liabilities from book value
            total_equity = (
                fundamentals.book_value_per_share * fundamentals.shares_outstanding
            )
            debt = fundamentals.total_debt or Decimal("0")
            total_assets = total_equity + debt
            
            asset_result = self.asset_based_valuation(
                total_assets=total_assets,
                total_liabilities=debt,
                intangible_assets=Decimal("0"),  # Conservative
                shares_outstanding=fundamentals.shares_outstanding,
            )
            if asset_result and asset_result.nav_per_share:
                methods_used.append(ValuationMethod.ASSET_BASED)
                intrinsic_values.append(asset_result.nav_per_share)
        else:
            warnings.append("Asset-based: No book value data")

        # EPV valuation
        epv_result = None
        if fundamentals.eps and fundamentals.shares_outstanding:
            # Estimate EBIT from EPS (rough approximation)
            eps = fundamentals.eps
            if eps > 0:
                # Assume 25% tax rate, back-calculate EBIT
                net_income = eps * fundamentals.shares_outstanding
                ebit_estimate = net_income / (1 - self.DEFAULT_TAX_RATE)
                
                epv_result = self.epv_valuation(
                    ebit=ebit_estimate,
                    tax_rate=self.DEFAULT_TAX_RATE,
                    maintenance_capex=Decimal("0"),  # Conservative
                    cost_of_capital=self.DEFAULT_DISCOUNT_RATE,
                    shares_outstanding=fundamentals.shares_outstanding,
                    excess_cash=fundamentals.total_cash or Decimal("0"),
                    total_debt=fundamentals.total_debt or Decimal("0"),
                )
                if epv_result and epv_result.epv_per_share:
                    methods_used.append(ValuationMethod.EPV)
                    intrinsic_values.append(epv_result.epv_per_share)
        else:
            warnings.append("EPV: No EPS or shares data")

        # Calculate composite metrics
        avg_value = None
        median_value = None
        margin = None

        if intrinsic_values:
            avg_value = self._round(sum(intrinsic_values) / len(intrinsic_values))
            sorted_values = sorted(intrinsic_values)
            mid = len(sorted_values) // 2
            if len(sorted_values) % 2 == 0:
                median_value = self._round(
                    (sorted_values[mid - 1] + sorted_values[mid]) / 2
                )
            else:
                median_value = sorted_values[mid]

            if current_price > 0 and median_value:
                margin = self.calculate_margin_of_safety(current_price, median_value)

        # Determine primary method
        primary_method = self._determine_primary_method(stock)

        # Confidence based on data completeness
        confidence = Decimal(len(methods_used) * 25)  # 25% per method

        return ValuationResult(
            symbol=stock.symbol,
            current_price=current_price,
            graham=graham_result,
            dcf=dcf_result,
            asset_based=asset_result,
            epv=epv_result,
            average_intrinsic_value=avg_value,
            median_intrinsic_value=median_value,
            margin_of_safety=margin,
            valuation_methods_used=methods_used,
            primary_method=primary_method,
            confidence_score=confidence,
            warnings=warnings,
        )

