import pytest
from app.services.fcf_projector import FCFProjector


class TestFCFProjector:
    def test_calculate_revenue_cagr(self):
        """Calculate compound annual growth rate from historical revenue."""
        projector = FCFProjector(
            historical_revenue=[100, 110, 121, 133.1],  # 10% growth
            historical_ebit=[20, 22, 24.2, 26.62],
            historical_da=[5, 5.5, 6, 6.5],
            historical_capex=[10, 11, 12, 13],
            historical_working_capital=[15, 16.5, 18, 19.8],
            tax_rate=0.25,
        )

        cagr = projector.revenue_cagr()
        assert abs(cagr - 0.10) < 0.01  # ~10%

    def test_calculate_operating_margin(self):
        """Calculate average operating margin from historical data."""
        projector = FCFProjector(
            historical_revenue=[100, 110, 121, 133.1],
            historical_ebit=[20, 22, 24.2, 26.62],  # 20% margin
            historical_da=[5, 5.5, 6, 6.5],
            historical_capex=[10, 11, 12, 13],
            historical_working_capital=[15, 16.5, 18, 19.8],
            tax_rate=0.25,
        )

        margin = projector.operating_margin()
        assert abs(margin - 0.20) < 0.01  # ~20%

    def test_calculate_da_ratio(self):
        """Calculate D&A as percentage of revenue."""
        projector = FCFProjector(
            historical_revenue=[100, 110, 121, 133.1],
            historical_ebit=[20, 22, 24.2, 26.62],
            historical_da=[5, 5.5, 6.05, 6.655],  # 5% of revenue
            historical_capex=[10, 11, 12, 13],
            historical_working_capital=[15, 16.5, 18, 19.8],
            tax_rate=0.25,
        )

        da_ratio = projector.da_to_revenue_ratio()
        assert abs(da_ratio - 0.05) < 0.01  # ~5%

    def test_calculate_capex_ratio(self):
        """Calculate CapEx as percentage of revenue."""
        projector = FCFProjector(
            historical_revenue=[100, 110, 121, 133.1],
            historical_ebit=[20, 22, 24.2, 26.62],
            historical_da=[5, 5.5, 6, 6.5],
            historical_capex=[10, 11, 12.1, 13.31],  # 10% of revenue
            historical_working_capital=[15, 16.5, 18, 19.8],
            tax_rate=0.25,
        )

        capex_ratio = projector.capex_to_revenue_ratio()
        assert abs(capex_ratio - 0.10) < 0.01  # ~10%

    def test_project_single_year(self):
        """Project FCF for a single year."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],  # 20% margin
            historical_da=[5],     # 5% of rev
            historical_capex=[10], # 10% of rev
            historical_working_capital=[15],
            tax_rate=0.25,
        )

        # Year 1 with 10% revenue growth
        # Revenue: 100 * 1.10 = 110
        # EBIT: 110 * 0.20 = 22
        # NOPAT: 22 * (1 - 0.25) = 16.5
        # D&A: 110 * 0.05 = 5.5
        # CapEx: 110 * 0.10 = 11
        # ΔWC: (110 * 0.15) - 15 = 1.5
        # FCF: 16.5 + 5.5 - 11 - 1.5 = 9.5

        fcf = projector.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=15,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.15,
        )

        assert abs(fcf["revenue"] - 110) < 0.01
        assert abs(fcf["ebit"] - 22) < 0.01
        assert abs(fcf["nopat"] - 16.5) < 0.01
        assert abs(fcf["fcf"] - 9.5) < 0.01

    def test_project_multiple_years(self):
        """Project FCF for multiple years."""
        projector = FCFProjector(
            historical_revenue=[100, 110, 121],
            historical_ebit=[20, 22, 24.2],
            historical_da=[5, 5.5, 6.05],
            historical_capex=[10, 11, 12.1],
            historical_working_capital=[15, 16.5, 18.15],
            tax_rate=0.25,
        )

        projections = projector.project(years=3)

        assert len(projections) == 3
        assert "revenue" in projections[0]
        assert "fcf" in projections[0]
        # Revenue should grow each year
        assert projections[1]["revenue"] > projections[0]["revenue"]
        assert projections[2]["revenue"] > projections[1]["revenue"]

    def test_allows_custom_growth_override(self):
        """User can override calculated growth rate."""
        projector = FCFProjector(
            historical_revenue=[100, 105],  # 5% historical growth
            historical_ebit=[20, 21],
            historical_da=[5, 5.25],
            historical_capex=[10, 10.5],
            historical_working_capital=[15, 15.75],
            tax_rate=0.25,
        )

        # Override with 15% growth
        projections = projector.project(years=1, revenue_growth=0.15)

        # Revenue should be 105 * 1.15 = 120.75
        assert abs(projections[0]["revenue"] - 120.75) < 0.01

    def test_handles_negative_working_capital_change(self):
        """Negative WC change (source of cash) increases FCF."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[20],  # High WC
            tax_rate=0.25,
        )

        # If WC ratio drops, ΔWC is negative (cash inflow)
        fcf = projector.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=20,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.10,  # Lower than prior 20%
        )

        # New WC = 110 * 0.10 = 11
        # ΔWC = 11 - 20 = -9 (cash release)
        assert fcf["delta_wc"] < 0
        # FCF should be higher due to WC release


