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

    def test_handles_none_tax_rate_with_default(self):
        """Uses default 25% tax rate when tax_rate is None (regression test)."""
        from app.services.fcf_projector import DEFAULT_TAX_RATE
        
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[15],
            tax_rate=None,  # Missing tax data
        )

        # Should use default tax rate
        assert projector.effective_tax_rate == DEFAULT_TAX_RATE
        assert projector.effective_tax_rate == 0.25

        # Should not crash when projecting
        fcf = projector.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=15,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.15,
        )

        # NOPAT should be calculated with default tax rate
        # Revenue = 110, EBIT = 22, NOPAT = 22 * 0.75 = 16.5
        assert abs(fcf["nopat"] - 16.5) < 0.01


class TestWCIncrementalMode:
    """Tests for working capital incremental intensity mode."""
    
    def test_level_based_wc_mode_default(self):
        """Default mode: WC = Revenue × WC_ratio."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[15],
            tax_rate=0.25,
            wc_mode="level",  # Default
        )
        
        fcf = projector.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=15,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.15,
        )
        
        # New WC = 110 * 0.15 = 16.5
        # ΔWC = 16.5 - 15 = 1.5
        assert abs(fcf["working_capital"] - 16.5) < 0.01
        assert abs(fcf["delta_wc"] - 1.5) < 0.01
    
    def test_incremental_wc_mode(self):
        """Incremental mode: ΔWC = ΔRevenue × WC_intensity."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[15],
            tax_rate=0.25,
            wc_mode="incremental",
        )
        
        fcf = projector.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=15,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.15,  # In incremental mode, this is WC intensity
        )
        
        # Revenue change = 110 - 100 = 10
        # ΔWC = 10 * 0.15 = 1.5
        # New WC = 15 + 1.5 = 16.5
        assert abs(fcf["delta_wc"] - 1.5) < 0.01
        assert abs(fcf["working_capital"] - 16.5) < 0.01
    
    def test_incremental_mode_with_high_growth(self):
        """Incremental mode handles high growth differently from level mode."""
        # Level-based mode
        projector_level = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[10],  # Low WC
            tax_rate=0.25,
            wc_mode="level",
        )
        
        # Incremental mode
        projector_incr = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[10],
            tax_rate=0.25,
            wc_mode="incremental",
        )
        
        # Project with 50% growth and 20% WC ratio
        fcf_level = projector_level.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=10,
            revenue_growth=0.50,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.20,
        )
        
        fcf_incr = projector_incr.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=10,
            revenue_growth=0.50,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.20,  # WC intensity
        )
        
        # Level: New WC = 150 * 0.20 = 30, ΔWC = 30 - 10 = 20
        # Incr: ΔRevenue = 50, ΔWC = 50 * 0.20 = 10
        assert abs(fcf_level["delta_wc"] - 20) < 0.01
        assert abs(fcf_incr["delta_wc"] - 10) < 0.01
        
        # Incremental mode results in higher FCF with high growth
        assert fcf_incr["fcf"] > fcf_level["fcf"]
    
    def test_incremental_mode_with_negative_growth(self):
        """Incremental mode handles negative growth (releases WC)."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[15],
            tax_rate=0.25,
            wc_mode="incremental",
        )
        
        fcf = projector.project_fcf_year(
            prior_revenue=100,
            prior_working_capital=15,
            revenue_growth=-0.10,  # Revenue declines
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.10,
            wc_ratio=0.15,
        )
        
        # Revenue change = 90 - 100 = -10
        # ΔWC = -10 * 0.15 = -1.5 (cash release)
        assert abs(fcf["delta_wc"] - (-1.5)) < 0.01
        assert fcf["delta_wc"] < 0  # WC release
    
    def test_project_method_respects_wc_mode(self):
        """Full projection respects wc_mode setting."""
        projector = FCFProjector(
            historical_revenue=[100, 110],
            historical_ebit=[20, 22],
            historical_da=[5, 5.5],
            historical_capex=[10, 11],
            historical_working_capital=[15, 16.5],
            tax_rate=0.25,
            wc_mode="incremental",
        )
        
        projections = projector.project(years=2, revenue_growth=0.10)
        
        # Should have projections
        assert len(projections) == 2
        # WC mode is used internally
        assert projections[0]["delta_wc"] is not None


class TestMultiStageGrowthIntegration:
    """Test FCFProjector with multi-stage growth schedules."""
    
    def test_growth_schedule_overrides_constant_growth(self):
        """When growth_schedule is provided, it overrides constant revenue_growth."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[15],
            tax_rate=0.25,
        )
        
        # Variable growth: 20%, 15%, 10%
        growth_schedule = [0.20, 0.15, 0.10]
        
        projections = projector.project(
            years=5,  # Ignored when growth_schedule provided
            revenue_growth=0.05,  # Also ignored
            growth_schedule=growth_schedule,
        )
        
        # Should have 3 years (from schedule), not 5
        assert len(projections) == 3
        
        # Verify revenues follow the schedule
        # Year 1: 100 * 1.20 = 120
        # Year 2: 120 * 1.15 = 138
        # Year 3: 138 * 1.10 = 151.8
        assert abs(projections[0]["revenue"] - 120) < 0.1
        assert abs(projections[1]["revenue"] - 138) < 0.1
        assert abs(projections[2]["revenue"] - 151.8) < 0.1
    
    def test_growth_schedule_with_fade(self):
        """Test variable growth with declining rates (fade)."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[100],
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        # High growth fading to low: 25%, 20%, 15%, 10%, 5%
        growth_schedule = [0.25, 0.20, 0.15, 0.10, 0.05]
        
        projections = projector.project(
            years=10,  # Ignored
            growth_schedule=growth_schedule,
        )
        
        assert len(projections) == 5
        
        # Each year should apply different growth
        expected_revenues = [1250, 1500, 1725, 1897.5, 1992.375]
        for i, proj in enumerate(projections):
            assert abs(proj["revenue"] - expected_revenues[i]) < 0.5
    
    def test_growth_schedule_with_negative_growth(self):
        """Test schedule with negative growth (turnaround scenarios)."""
        projector = FCFProjector(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[10],
            historical_working_capital=[15],
            tax_rate=0.25,
        )
        
        # Decline then recovery
        growth_schedule = [-0.10, -0.05, 0.0, 0.05, 0.10]
        
        projections = projector.project(growth_schedule=growth_schedule, years=1)
        
        assert len(projections) == 5
        
        # Revenue should dip then recover
        assert projections[0]["revenue"] < 100  # Decline
        assert projections[1]["revenue"] < projections[0]["revenue"]  # More decline
        assert projections[2]["revenue"] == projections[1]["revenue"]  # Flat
        assert projections[3]["revenue"] > projections[2]["revenue"]  # Growth
        assert projections[4]["revenue"] > projections[3]["revenue"]  # More growth


class TestEconomicsScheduleIntegration:
    """
    Test FCFProjector with year-by-year economics schedules.
    
    This enables modeling of operating leverage (margin expansion),
    economies of scale (capex reduction), and working capital efficiency
    improvements as a company matures.
    """
    
    def test_margin_schedule_applies_year_by_year(self):
        """Operating margin schedule should vary margins per year."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],  # 20% margin
            historical_da=[50],
            historical_capex=[100],
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        # Margin expansion: 20% → 25% → 30%
        margin_schedule = [0.20, 0.25, 0.30]
        growth_schedule = [0.10, 0.10, 0.10]
        
        projections = projector.project(
            years=3,
            growth_schedule=growth_schedule,
            margin_schedule=margin_schedule,
        )
        
        assert len(projections) == 3
        
        # Year 1: Revenue 1100, EBIT = 1100 * 0.20 = 220
        # Year 2: Revenue 1210, EBIT = 1210 * 0.25 = 302.5
        # Year 3: Revenue 1331, EBIT = 1331 * 0.30 = 399.3
        assert abs(projections[0]["ebit"] - 220) < 1
        assert abs(projections[1]["ebit"] - 302.5) < 1
        assert abs(projections[2]["ebit"] - 399.3) < 1
    
    def test_capex_schedule_applies_year_by_year(self):
        """CapEx schedule should vary CapEx per year."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[100],  # 10%
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        # CapEx ratio decline: 10% → 8% → 6%
        capex_schedule = [0.10, 0.08, 0.06]
        growth_schedule = [0.10, 0.10, 0.10]
        
        projections = projector.project(
            years=3,
            growth_schedule=growth_schedule,
            capex_schedule=capex_schedule,
        )
        
        # Year 1: Revenue 1100, CapEx = 1100 * 0.10 = 110
        # Year 2: Revenue 1210, CapEx = 1210 * 0.08 = 96.8
        # Year 3: Revenue 1331, CapEx = 1331 * 0.06 = 79.86
        assert abs(projections[0]["capex"] - 110) < 1
        assert abs(projections[1]["capex"] - 96.8) < 1
        assert abs(projections[2]["capex"] - 79.86) < 1
    
    def test_wc_schedule_applies_year_by_year(self):
        """Working capital schedule should vary WC per year (level mode)."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[100],
            historical_working_capital=[150],  # 15%
            tax_rate=0.25,
        )
        
        # WC efficiency improvement: 15% → 12% → 10%
        wc_schedule = [0.15, 0.12, 0.10]
        growth_schedule = [0.10, 0.10, 0.10]
        
        projections = projector.project(
            years=3,
            growth_schedule=growth_schedule,
            wc_schedule=wc_schedule,
            wc_mode="level",
        )
        
        # Year 1: Revenue 1100, WC = 1100 * 0.15 = 165
        # Year 2: Revenue 1210, WC = 1210 * 0.12 = 145.2
        # Year 3: Revenue 1331, WC = 1331 * 0.10 = 133.1
        assert abs(projections[0]["working_capital"] - 165) < 1
        assert abs(projections[1]["working_capital"] - 145.2) < 1
        assert abs(projections[2]["working_capital"] - 133.1) < 1
    
    def test_all_schedules_combined(self):
        """Test all economics schedules working together."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[100],
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        # High-growth transitioning to mature
        growth_schedule = [0.20, 0.15, 0.10]
        margin_schedule = [0.20, 0.22, 0.25]   # Margin expansion
        capex_schedule = [0.10, 0.08, 0.06]    # CapEx declining
        wc_schedule = [0.15, 0.13, 0.11]       # WC efficiency
        
        projections = projector.project(
            years=3,
            growth_schedule=growth_schedule,
            margin_schedule=margin_schedule,
            capex_schedule=capex_schedule,
            wc_schedule=wc_schedule,
        )
        
        assert len(projections) == 3
        
        # Verify each year uses correct parameters
        # Year 1: Rev = 1200, EBIT = 240 (20%), CapEx = 120 (10%), WC = 180 (15%)
        assert abs(projections[0]["revenue"] - 1200) < 1
        assert abs(projections[0]["ebit"] - 240) < 1
        assert abs(projections[0]["capex"] - 120) < 1
        assert abs(projections[0]["working_capital"] - 180) < 1
    
    def test_schedule_shorter_than_growth_schedule(self):
        """When economics schedule is shorter, last value should repeat."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[100],
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        growth_schedule = [0.10, 0.10, 0.10, 0.10]  # 4 years
        margin_schedule = [0.20, 0.25]  # Only 2 years specified
        
        projections = projector.project(
            years=4,
            growth_schedule=growth_schedule,
            margin_schedule=margin_schedule,
        )
        
        assert len(projections) == 4
        
        # Years 3 & 4 should use last margin (0.25)
        margin_year3 = projections[2]["ebit"] / projections[2]["revenue"]
        margin_year4 = projections[3]["ebit"] / projections[3]["revenue"]
        assert abs(margin_year3 - 0.25) < 0.001
        assert abs(margin_year4 - 0.25) < 0.001
    
    def test_none_schedule_uses_constant_value(self):
        """When schedule is None, constant value is used (backward compatible)."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[100],
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        projections = projector.project(
            years=3,
            operating_margin=0.22,  # Constant margin
            margin_schedule=None,   # No schedule
        )
        
        # All years should use 22% margin
        for proj in projections:
            actual_margin = proj["ebit"] / proj["revenue"]
            assert abs(actual_margin - 0.22) < 0.001
    
    def test_da_schedule_applies_year_by_year(self):
        """D&A schedule should vary D&A per year."""
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],  # 5%
            historical_capex=[100],
            historical_working_capital=[150],
            tax_rate=0.25,
        )
        
        # D&A ratio decline (assets maturing): 5% → 4% → 3%
        da_schedule = [0.05, 0.04, 0.03]
        growth_schedule = [0.10, 0.10, 0.10]
        
        projections = projector.project(
            years=3,
            growth_schedule=growth_schedule,
            da_schedule=da_schedule,
        )
        
        # Year 1: Revenue 1100, D&A = 1100 * 0.05 = 55
        # Year 2: Revenue 1210, D&A = 1210 * 0.04 = 48.4
        # Year 3: Revenue 1331, D&A = 1331 * 0.03 = 39.93
        assert abs(projections[0]["da"] - 55) < 1
        assert abs(projections[1]["da"] - 48.4) < 1
        assert abs(projections[2]["da"] - 39.93) < 1


class TestConservativeFCF:
    """
    NOTES2.md: Conservative FCF Toggle (FCF - SBC)
    
    Some investors treat Stock-Based Compensation as a real cash expense
    because it represents value transferred from shareholders to employees.
    
    Conservative FCF = NOPAT + D&A - CapEx - ΔWC - SBC
    
    Where SBC is projected as a % of revenue (like other operating ratios).
    """
    
    def test_sbc_ratio_calculation(self):
        """
        Calculate SBC as percentage of revenue from historical data.
        """
        projector = FCFProjector(
            historical_revenue=[100, 110, 121],
            historical_ebit=[20, 22, 24.2],
            historical_da=[5, 5.5, 6.05],
            historical_capex=[10, 11, 12.1],
            historical_working_capital=[10, 11, 12.1],
            historical_sbc=[5, 5.5, 6.05],  # 5% of revenue
            tax_rate=0.25,
        )
        
        sbc_ratio = projector.sbc_to_revenue_ratio()
        assert abs(sbc_ratio - 0.05) < 0.01, "SBC should be ~5% of revenue"
    
    def test_sbc_ratio_defaults_to_zero(self):
        """
        When no historical SBC data, ratio should be 0.
        """
        projector = FCFProjector(
            historical_revenue=[100, 110],
            historical_ebit=[20, 22],
            historical_da=[5, 5.5],
            historical_capex=[10, 11],
            historical_working_capital=[10, 11],
            # No historical_sbc provided
            tax_rate=0.25,
        )
        
        sbc_ratio = projector.sbc_to_revenue_ratio()
        assert sbc_ratio == 0.0, "SBC ratio should default to 0"
    
    def test_conservative_fcf_subtracts_sbc(self):
        """
        When subtract_sbc=True, FCF should be reduced by SBC.
        """
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[80],
            historical_working_capital=[100],
            tax_rate=0.25,
        )
        
        # Without SBC (standard FCF)
        standard_projections = projector.project(
            years=1,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.10,
            sbc_ratio=None,  # No SBC subtraction
        )
        
        # With SBC (conservative FCF) - 5% of revenue
        conservative_projections = projector.project(
            years=1,
            revenue_growth=0.10,
            operating_margin=0.20,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.10,
            sbc_ratio=0.05,  # 5% SBC
        )
        
        # Revenue = 1000 * 1.10 = 1100
        # SBC = 1100 * 0.05 = 55
        # Conservative FCF should be 55 less than standard FCF
        expected_sbc = 1100 * 0.05
        fcf_diff = standard_projections[0]["fcf"] - conservative_projections[0]["fcf"]
        
        assert abs(fcf_diff - expected_sbc) < 1, (
            f"Conservative FCF should be {expected_sbc} less than standard. "
            f"Actual diff: {fcf_diff}"
        )
        
        # Verify SBC is tracked in projection
        assert "sbc" in conservative_projections[0], "SBC should be in projection dict"
        assert abs(conservative_projections[0]["sbc"] - expected_sbc) < 1
    
    def test_conservative_fcf_with_sbc_schedule(self):
        """
        SBC can also be provided as a per-year schedule (like other economics).
        """
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[200],
            historical_da=[50],
            historical_capex=[80],
            historical_working_capital=[100],
            tax_rate=0.25,
        )
        
        # SBC schedule: 5%, 4%, 3% (declining as company matures)
        sbc_schedule = [0.05, 0.04, 0.03]
        growth_schedule = [0.10, 0.10, 0.10]
        
        projections = projector.project(
            years=3,
            growth_schedule=growth_schedule,
            sbc_schedule=sbc_schedule,
        )
        
        # Year 1: Revenue 1100, SBC = 55
        # Year 2: Revenue 1210, SBC = 48.4
        # Year 3: Revenue 1331, SBC = 39.93
        assert abs(projections[0]["sbc"] - 55) < 1
        assert abs(projections[1]["sbc"] - 48.4) < 1
        assert abs(projections[2]["sbc"] - 39.93) < 1



