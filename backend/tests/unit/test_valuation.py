"""
Unit tests for valuation calculations.

TDD: These tests are written FIRST, before the implementation.
"""

import pytest
from decimal import Decimal

from app.models.stock import Stock, StockFundamentals
from app.services.valuation import ValuationService


class TestGrahamValuation:
    """Tests for Graham's intrinsic value formula."""

    def test_graham_basic_calculation(self):
        """
        Test basic Graham formula: V = EPS × (8.5 + 2g) × 4.4 / Y
        
        Given:
            EPS = $10
            Growth rate = 7% (0.07)
            AAA yield = 5% (0.05)
        
        Expected:
            V = 10 × (8.5 + 2×7) × 4.4 / 5
            V = 10 × 22.5 × 0.88
            V = $198.00
        """
        service = ValuationService()
        
        result = service.graham_valuation(
            eps=Decimal("10.00"),
            growth_rate=Decimal("0.07"),
            aaa_yield=Decimal("0.05"),
        )
        
        assert result is not None
        assert result.intrinsic_value is not None
        # Allow small floating point variance
        assert Decimal("197.00") <= result.intrinsic_value <= Decimal("199.00")

    def test_graham_no_growth(self):
        """
        Test Graham formula with zero growth.
        
        V = EPS × 8.5 × 4.4 / Y
        V = 10 × 8.5 × 0.88 = $74.80
        """
        service = ValuationService()
        
        result = service.graham_valuation(
            eps=Decimal("10.00"),
            growth_rate=Decimal("0"),
            aaa_yield=Decimal("0.05"),
        )
        
        assert result is not None
        assert Decimal("74.00") <= result.intrinsic_value <= Decimal("75.00")

    def test_graham_negative_eps_returns_none(self):
        """Graham valuation should return None for negative earnings."""
        service = ValuationService()
        
        result = service.graham_valuation(
            eps=Decimal("-5.00"),
            growth_rate=Decimal("0.07"),
            aaa_yield=Decimal("0.05"),
        )
        
        assert result is None or result.intrinsic_value is None

    def test_graham_high_growth_capped(self):
        """
        Graham formula should cap unrealistic growth rates.
        Growth above 15% should be capped to prevent absurd valuations.
        """
        service = ValuationService()
        
        result = service.graham_valuation(
            eps=Decimal("10.00"),
            growth_rate=Decimal("0.50"),  # 50% growth - unrealistic
            aaa_yield=Decimal("0.05"),
        )
        
        assert result is not None
        # Should be capped, not astronomical
        assert result.intrinsic_value < Decimal("500.00")


class TestDCFValuation:
    """Tests for Discounted Cash Flow valuation."""

    def test_dcf_basic_calculation(self):
        """
        Test basic DCF calculation.
        
        Given:
            FCF = $100M
            Growth rate = 10% for 5 years
            Terminal growth = 2.5%
            Discount rate = 10%
            Shares = 10M
        
        The DCF should project FCFs, calculate terminal value,
        discount everything to present value.
        """
        service = ValuationService()
        
        result = service.dcf_valuation(
            fcf_current=Decimal("100_000_000"),
            growth_rate_high=Decimal("0.10"),
            growth_rate_terminal=Decimal("0.025"),
            high_growth_years=5,
            discount_rate=Decimal("0.10"),
            shares_outstanding=10_000_000,
        )
        
        assert result is not None
        assert result.intrinsic_value_per_share is not None
        assert result.intrinsic_value_per_share > 0
        assert result.terminal_value is not None
        assert len(result.projected_fcfs) == 5

    def test_dcf_negative_fcf_handled(self):
        """DCF should handle negative free cash flow gracefully."""
        service = ValuationService()
        
        result = service.dcf_valuation(
            fcf_current=Decimal("-50_000_000"),
            growth_rate_high=Decimal("0.10"),
            growth_rate_terminal=Decimal("0.025"),
            high_growth_years=5,
            discount_rate=Decimal("0.10"),
            shares_outstanding=10_000_000,
        )
        
        # Should either return None or a result with a warning
        assert result is None or result.intrinsic_value_per_share is None

    def test_dcf_terminal_growth_must_be_less_than_discount(self):
        """Terminal growth rate must be less than discount rate."""
        service = ValuationService()
        
        # Terminal growth >= discount rate would give infinite/negative value
        result = service.dcf_valuation(
            fcf_current=Decimal("100_000_000"),
            growth_rate_high=Decimal("0.10"),
            growth_rate_terminal=Decimal("0.12"),  # Higher than discount!
            high_growth_years=5,
            discount_rate=Decimal("0.10"),
            shares_outstanding=10_000_000,
        )
        
        assert result is None or result.intrinsic_value_per_share is None


class TestAssetBasedValuation:
    """Tests for asset-based (book value) valuation."""

    def test_asset_based_basic(self):
        """
        Test basic NAV calculation.
        
        NAV = Total Assets - Total Liabilities
        NAV per share = NAV / Shares Outstanding
        """
        service = ValuationService()
        
        result = service.asset_based_valuation(
            total_assets=Decimal("1_000_000_000"),
            total_liabilities=Decimal("400_000_000"),
            intangible_assets=Decimal("100_000_000"),
            shares_outstanding=10_000_000,
        )
        
        assert result is not None
        # NAV = 1B - 400M = 600M -> $60 per share
        assert result.nav_per_share == Decimal("60.00")
        # Tangible BV = 1B - 100M - 400M = 500M -> $50 per share
        assert result.tbv_per_share == Decimal("50.00")

    def test_asset_based_with_discount(self):
        """Test NAV with asset discount (conservative valuation)."""
        service = ValuationService()
        
        result = service.asset_based_valuation(
            total_assets=Decimal("1_000_000_000"),
            total_liabilities=Decimal("400_000_000"),
            intangible_assets=Decimal("0"),
            shares_outstanding=10_000_000,
            asset_discount=Decimal("0.20"),  # 20% discount on assets
        )
        
        assert result is not None
        # Assets after discount: 800M - 400M = 400M -> $40 per share
        assert result.nav_per_share == Decimal("40.00")

    def test_asset_based_negative_equity(self):
        """Test when liabilities exceed assets."""
        service = ValuationService()
        
        result = service.asset_based_valuation(
            total_assets=Decimal("400_000_000"),
            total_liabilities=Decimal("600_000_000"),  # More than assets!
            intangible_assets=Decimal("0"),
            shares_outstanding=10_000_000,
        )
        
        assert result is not None
        # Should show negative NAV
        assert result.nav_per_share < 0


class TestEPVValuation:
    """Tests for Earnings Power Value valuation."""

    def test_epv_basic_calculation(self):
        """
        Test basic EPV calculation.
        
        EPV = Normalized Earnings / Cost of Capital
        
        Given:
            EBIT = $200M
            Tax rate = 25%
            Maintenance CapEx = $20M
            Cost of capital = 10%
            Shares = 10M
        
        Normalized earnings = 200M × (1 - 0.25) - 20M = 150M - 20M = 130M
        EPV (operations) = 130M / 0.10 = $1.3B
        EPV per share = $130
        """
        service = ValuationService()
        
        result = service.epv_valuation(
            ebit=Decimal("200_000_000"),
            tax_rate=Decimal("0.25"),
            maintenance_capex=Decimal("20_000_000"),
            cost_of_capital=Decimal("0.10"),
            shares_outstanding=10_000_000,
        )
        
        assert result is not None
        assert result.epv_per_share is not None
        assert Decimal("129.00") <= result.epv_per_share <= Decimal("131.00")

    def test_epv_with_adjustments(self):
        """
        Test EPV with excess cash and debt adjustments.
        
        EPV equity = EPV operations + Excess Cash - Debt
        """
        service = ValuationService()
        
        result = service.epv_valuation(
            ebit=Decimal("200_000_000"),
            tax_rate=Decimal("0.25"),
            maintenance_capex=Decimal("20_000_000"),
            cost_of_capital=Decimal("0.10"),
            shares_outstanding=10_000_000,
            excess_cash=Decimal("200_000_000"),  # +$200M
            total_debt=Decimal("100_000_000"),   # -$100M
        )
        
        assert result is not None
        # EPV operations = $1.3B, + 200M - 100M = $1.4B
        # Per share = $140
        assert Decimal("139.00") <= result.epv_per_share <= Decimal("141.00")

    def test_epv_negative_ebit(self):
        """EPV should handle negative EBIT appropriately."""
        service = ValuationService()
        
        result = service.epv_valuation(
            ebit=Decimal("-50_000_000"),
            tax_rate=Decimal("0.25"),
            maintenance_capex=Decimal("20_000_000"),
            cost_of_capital=Decimal("0.10"),
            shares_outstanding=10_000_000,
        )
        
        assert result is None or result.epv_per_share is None


class TestMarginOfSafety:
    """Tests for margin of safety calculations."""

    def test_margin_of_safety_undervalued(self):
        """Test margin of safety when stock is undervalued."""
        service = ValuationService()
        
        result = service.calculate_margin_of_safety(
            current_price=Decimal("75.00"),
            intrinsic_value=Decimal("100.00"),
        )
        
        assert result is not None
        assert result.margin_of_safety == Decimal("25.00")  # 25%
        assert result.is_undervalued is True

    def test_margin_of_safety_overvalued(self):
        """Test margin of safety when stock is overvalued."""
        service = ValuationService()
        
        result = service.calculate_margin_of_safety(
            current_price=Decimal("120.00"),
            intrinsic_value=Decimal("100.00"),
        )
        
        assert result is not None
        assert result.margin_of_safety == Decimal("-20.00")  # -20%
        assert result.is_undervalued is False

    def test_margin_of_safety_threshold(self):
        """Test margin of safety with custom threshold."""
        service = ValuationService()
        
        # 20% margin - not enough for 25% threshold
        result = service.calculate_margin_of_safety(
            current_price=Decimal("80.00"),
            intrinsic_value=Decimal("100.00"),
            min_margin_required=Decimal("0.25"),
        )
        
        assert result is not None
        assert result.margin_of_safety == Decimal("20.00")
        # 20% < 25% threshold, so not a strong buy
        assert result.is_undervalued is False


class TestValuationIntegration:
    """Integration tests for complete stock valuation."""

    def test_full_valuation_value_stock(self, sample_value_stock: Stock):
        """Test complete valuation of a value stock."""
        service = ValuationService()
        
        result = service.calculate_full_valuation(sample_value_stock)
        
        assert result is not None
        assert result.symbol == "VALUE"
        assert len(result.valuation_methods_used) > 0
        assert result.margin_of_safety is not None

    def test_full_valuation_selects_appropriate_method(
        self, sample_financial_stock: Stock
    ):
        """Test that financial stocks use asset-based as primary method."""
        service = ValuationService()
        
        result = service.calculate_full_valuation(sample_financial_stock)
        
        assert result is not None
        # Financial stocks should primarily use asset-based valuation
        from app.models.valuation import ValuationMethod
        assert result.primary_method == ValuationMethod.ASSET_BASED

    def test_full_valuation_handles_missing_data(self):
        """Test valuation with incomplete fundamental data."""
        service = ValuationService()
        
        # Stock with minimal data
        incomplete_stock = Stock(
            symbol="SPRSE",
            name="Sparse Data Inc",
            fundamentals=StockFundamentals(
                eps=Decimal("5.00"),
                market_cap=Decimal("1_000_000_000"),
                # Most fields missing
                data_gaps=["pe_ratio", "book_value", "fcf", "debt"],
            ),
        )
        incomplete_stock.price = None
        
        result = service.calculate_full_valuation(incomplete_stock)
        
        # Should still produce something, with warnings
        assert result is not None
        assert len(result.warnings) > 0

