import pytest
from app.services.multi_stage_growth import (
    GrowthStage,
    MultiStageGrowthModel,
    create_fade_schedule,
    calculate_growth_schedule,
    FadeMode,
    create_step_schedule,
    capital_intensive_model,
)


class TestGrowthStage:
    """Tests for GrowthStage dataclass."""
    
    def test_growth_stage_creation(self):
        """Can create a growth stage."""
        stage = GrowthStage(
            name="High Growth",
            years=5,
            growth_rate=0.15,
        )
        assert stage.name == "High Growth"
        assert stage.years == 5
        assert stage.growth_rate == 0.15
    
    def test_growth_stage_with_fade(self):
        """Growth stage can have end_growth_rate for fading."""
        stage = GrowthStage(
            name="Fade",
            years=5,
            growth_rate=0.15,
            end_growth_rate=0.05,  # Linear fade from 15% to 5%
        )
        assert stage.end_growth_rate == 0.05


class TestCreateFadeSchedule:
    """Tests for the fade schedule helper."""
    
    def test_linear_fade(self):
        """Create linear fade from start to end rate."""
        schedule = create_fade_schedule(
            start_rate=0.20,
            end_rate=0.05,
            years=4,
        )
        
        assert len(schedule) == 4
        # Should decrease linearly
        assert schedule[0] == 0.20
        assert abs(schedule[-1] - 0.05) < 0.001
        # Each step should decrease
        for i in range(1, len(schedule)):
            assert schedule[i] < schedule[i-1]
    
    def test_single_year_fade(self):
        """Single year fade returns start rate."""
        schedule = create_fade_schedule(0.20, 0.05, 1)
        assert len(schedule) == 1
        assert schedule[0] == 0.20
    
    def test_no_change_fade(self):
        """Same start and end returns constant rate."""
        schedule = create_fade_schedule(0.10, 0.10, 5)
        assert len(schedule) == 5
        assert all(r == 0.10 for r in schedule)


class TestCalculateGrowthSchedule:
    """Tests for converting stages to year-by-year schedule."""
    
    def test_single_stage_constant_growth(self):
        """Single stage produces constant growth rates."""
        stages = [GrowthStage("Growth", years=5, growth_rate=0.10)]
        schedule = calculate_growth_schedule(stages)
        
        assert len(schedule) == 5
        assert all(r == 0.10 for r in schedule)
    
    def test_two_stage_model(self):
        """Two stages: high growth then lower growth."""
        stages = [
            GrowthStage("High", years=3, growth_rate=0.20),
            GrowthStage("Stable", years=2, growth_rate=0.08),
        ]
        schedule = calculate_growth_schedule(stages)
        
        assert len(schedule) == 5
        assert schedule[:3] == [0.20, 0.20, 0.20]
        assert schedule[3:] == [0.08, 0.08]
    
    def test_fade_stage(self):
        """Stage with end_growth_rate creates linear fade."""
        stages = [
            GrowthStage("Fade", years=4, growth_rate=0.20, end_growth_rate=0.05),
        ]
        schedule = calculate_growth_schedule(stages)
        
        assert len(schedule) == 4
        assert schedule[0] == 0.20
        assert abs(schedule[-1] - 0.05) < 0.001
    
    def test_three_stage_model(self):
        """Classic three-stage: high growth → fade → terminal approach."""
        stages = [
            GrowthStage("High Growth", years=3, growth_rate=0.25),
            GrowthStage("Fade", years=4, growth_rate=0.25, end_growth_rate=0.08),
            GrowthStage("Mature", years=3, growth_rate=0.05),
        ]
        schedule = calculate_growth_schedule(stages)
        
        assert len(schedule) == 10
        # High growth phase
        assert schedule[0] == 0.25
        assert schedule[1] == 0.25
        assert schedule[2] == 0.25
        # Fade phase starts at 25%, ends at 8%
        assert schedule[3] == 0.25
        assert abs(schedule[6] - 0.08) < 0.001
        # Mature phase
        assert schedule[7:] == [0.05, 0.05, 0.05]


class TestMultiStageGrowthModel:
    """Tests for the multi-stage growth model."""
    
    @pytest.fixture
    def simple_model(self):
        """Simple two-stage model."""
        return MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=3, growth_rate=0.15),
                GrowthStage("Stable", years=2, growth_rate=0.05),
            ],
            terminal_growth_rate=0.03,
        )
    
    def test_total_projection_years(self, simple_model):
        """Total years is sum of all stage years."""
        assert simple_model.total_projection_years == 5
    
    def test_growth_schedule(self, simple_model):
        """Growth schedule matches stages."""
        schedule = simple_model.growth_schedule
        assert len(schedule) == 5
        assert schedule[:3] == [0.15, 0.15, 0.15]
        assert schedule[3:] == [0.05, 0.05]
    
    def test_project_revenue(self, simple_model):
        """Project revenue using multi-stage growth."""
        base_revenue = 100
        revenues = simple_model.project_revenue(base_revenue)
        
        assert len(revenues) == 5
        # Year 1: 100 * 1.15 = 115
        assert abs(revenues[0] - 115) < 0.1
        # Year 3: 100 * 1.15^3 ≈ 152.09
        assert abs(revenues[2] - 152.09) < 0.5
        # Year 5: (Year 3 revenue) * 1.05^2
        expected_y5 = 152.09 * 1.05 * 1.05
        assert abs(revenues[4] - expected_y5) < 1.0
    
    def test_three_stage_with_fade(self):
        """Full three-stage model with fade period."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High", years=2, growth_rate=0.20),
                GrowthStage("Fade", years=3, growth_rate=0.20, end_growth_rate=0.08),
                GrowthStage("Mature", years=2, growth_rate=0.05),
            ],
            terminal_growth_rate=0.03,
        )
        
        assert model.total_projection_years == 7
        
        schedule = model.growth_schedule
        assert schedule[0] == 0.20
        assert schedule[1] == 0.20
        # Fade starts at 0.20
        assert schedule[2] == 0.20
        # Fade ends near 0.08
        assert abs(schedule[4] - 0.08) < 0.01
        # Mature phase
        assert schedule[5] == 0.05
        assert schedule[6] == 0.05
    
    def test_get_stage_description(self):
        """Model can describe its structure."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=5, growth_rate=0.15),
            ],
            terminal_growth_rate=0.03,
        )
        
        desc = model.describe()
        assert "Growth" in desc
        assert "5" in desc
        assert "15" in desc or "0.15" in desc
    
    def test_empty_stages_raises(self):
        """Model requires at least one stage."""
        with pytest.raises(ValueError, match="(?i)at least one"):
            MultiStageGrowthModel(stages=[], terminal_growth_rate=0.03)
    
    def test_typical_high_growth_company(self):
        """Model a typical high-growth tech company."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Hypergrowth", years=2, growth_rate=0.30),
                GrowthStage("High Growth", years=3, growth_rate=0.20),
                GrowthStage("Fade to Maturity", years=3, growth_rate=0.20, end_growth_rate=0.08),
                GrowthStage("Mature", years=2, growth_rate=0.05),
            ],
            terminal_growth_rate=0.03,
        )
        
        base_revenue = 1000
        revenues = model.project_revenue(base_revenue)
        
        # Should have 10 years of projections
        assert len(revenues) == 10
        # Final revenue should be significantly higher
        assert revenues[-1] > base_revenue * 3


class TestEconomicsFade:
    """
    Tests for fading margins, CapEx, and WC ratios.
    
    Problem: Current model only fades revenue growth, but professional DCF
    requires margins, CapEx, and Working Capital to also fade to steady-state
    values as companies mature.
    
    Example: High-growth company starts with:
    - 30% operating margin (competitive advantage)
    - 15% CapEx/Revenue (heavy investment)
    - 20% WC/Revenue (growth requires working capital)
    
    But over time these should fade to industry steady-state:
    - 20% operating margin (competitive pressure)
    - 5% CapEx/Revenue (maintenance only)
    - 10% WC/Revenue (mature operations)
    """
    
    def test_growth_stage_supports_margin_fade(self):
        """GrowthStage can specify start and end operating margins."""
        stage = GrowthStage(
            name="Fade",
            years=5,
            growth_rate=0.15,
            operating_margin=0.30,
            end_operating_margin=0.20,  # Fade from 30% to 20%
        )
        assert stage.operating_margin == 0.30
        assert stage.end_operating_margin == 0.20
    
    def test_growth_stage_supports_capex_fade(self):
        """GrowthStage can specify start and end CapEx ratios."""
        stage = GrowthStage(
            name="Fade",
            years=5,
            growth_rate=0.15,
            capex_ratio=0.15,
            end_capex_ratio=0.05,  # Fade from 15% to 5%
        )
        assert stage.capex_ratio == 0.15
        assert stage.end_capex_ratio == 0.05
    
    def test_growth_stage_supports_wc_fade(self):
        """GrowthStage can specify start and end WC ratios."""
        stage = GrowthStage(
            name="Fade",
            years=5,
            growth_rate=0.15,
            wc_ratio=0.20,
            end_wc_ratio=0.10,  # Fade from 20% to 10%
        )
        assert stage.wc_ratio == 0.20
        assert stage.end_wc_ratio == 0.10
    
    def test_model_generates_margin_schedule(self):
        """MultiStageGrowthModel generates year-by-year margin schedule."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High", years=3, growth_rate=0.20, operating_margin=0.30),
                GrowthStage("Fade", years=4, growth_rate=0.15, operating_margin=0.30, 
                           end_operating_margin=0.20),
                GrowthStage("Mature", years=3, growth_rate=0.05, operating_margin=0.20),
            ],
            terminal_growth_rate=0.03,
        )
        
        margins = model.margin_schedule
        assert len(margins) == 10
        # High growth phase: constant 30%
        assert margins[0] == 0.30
        assert margins[2] == 0.30
        # Fade phase: 30% → 20%
        assert margins[3] == 0.30  # Start of fade
        assert abs(margins[6] - 0.20) < 0.01  # End of fade
        # Mature phase: constant 20%
        assert margins[7] == 0.20
        assert margins[9] == 0.20
    
    def test_model_generates_capex_schedule(self):
        """MultiStageGrowthModel generates year-by-year CapEx schedule."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High", years=2, growth_rate=0.20, capex_ratio=0.15),
                GrowthStage("Fade", years=3, growth_rate=0.15, capex_ratio=0.15, 
                           end_capex_ratio=0.05),
            ],
            terminal_growth_rate=0.03,
        )
        
        capex = model.capex_schedule
        assert len(capex) == 5
        assert capex[0] == 0.15
        assert capex[1] == 0.15
        assert capex[2] == 0.15  # Start of fade
        assert abs(capex[4] - 0.05) < 0.01  # End of fade
    
    def test_model_generates_wc_schedule(self):
        """MultiStageGrowthModel generates year-by-year WC schedule."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=3, growth_rate=0.20, wc_ratio=0.18),
                GrowthStage("Fade", years=2, growth_rate=0.10, wc_ratio=0.18, 
                           end_wc_ratio=0.12),
            ],
            terminal_growth_rate=0.03,
        )
        
        wc = model.wc_schedule
        assert len(wc) == 5
        assert wc[0] == 0.18
        assert wc[2] == 0.18
        assert wc[3] == 0.18  # Start of fade
        assert abs(wc[4] - 0.12) < 0.01  # End of fade
    
    def test_project_full_economics(self):
        """Model can project complete economics (revenue, margin, capex, wc)."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High Growth", years=2, growth_rate=0.25,
                           operating_margin=0.25, capex_ratio=0.12, wc_ratio=0.15),
                GrowthStage("Fade", years=3, growth_rate=0.15, 
                           operating_margin=0.25, end_operating_margin=0.18,
                           capex_ratio=0.12, end_capex_ratio=0.06,
                           wc_ratio=0.15, end_wc_ratio=0.10),
            ],
            terminal_growth_rate=0.03,
        )
        
        projections = model.project_economics(base_revenue=1000)
        
        assert len(projections) == 5
        # Check first year
        assert projections[0]["revenue"] == pytest.approx(1250, rel=0.01)  # 1000 * 1.25
        assert projections[0]["operating_margin"] == 0.25
        assert projections[0]["capex_ratio"] == 0.12
        assert projections[0]["wc_ratio"] == 0.15
        # Check final year (end of fade)
        assert projections[4]["operating_margin"] == pytest.approx(0.18, rel=0.01)
        assert projections[4]["capex_ratio"] == pytest.approx(0.06, rel=0.01)
        assert projections[4]["wc_ratio"] == pytest.approx(0.10, rel=0.01)
    
    def test_missing_economics_uses_none(self):
        """Economics fields default to None when not specified."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=3, growth_rate=0.15),  # No economics
            ],
            terminal_growth_rate=0.03,
        )
        
        # Schedules should be None if not specified
        assert model.margin_schedule is None
        assert model.capex_schedule is None
        assert model.wc_schedule is None
    
    def test_partial_economics_uses_available(self):
        """Can specify only some economics fields."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=3, growth_rate=0.15, 
                           operating_margin=0.25),  # Only margin, no capex/wc
            ],
            terminal_growth_rate=0.03,
        )
        
        assert model.margin_schedule is not None
        assert len(model.margin_schedule) == 3
        assert model.capex_schedule is None
        assert model.wc_schedule is None


class TestScheduleLengthConsistency:
    """
    P1 Bug: schedule length can mismatch projection_years after mutation.
    
    The model calculates schedules in __post_init__, but stages is mutable.
    If stages is modified after init, total_projection_years would mismatch
    the actual schedule lengths.
    """
    
    def test_schedule_length_matches_total_years(self):
        """All schedules should have length == total_projection_years."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High", years=3, growth_rate=0.20,
                           operating_margin=0.25, capex_ratio=0.12, wc_ratio=0.15),
                GrowthStage("Fade", years=4, growth_rate=0.15, end_growth_rate=0.05,
                           operating_margin=0.25, end_operating_margin=0.18),
            ],
            terminal_growth_rate=0.03,
        )
        
        # All should be consistent
        assert len(model.growth_schedule) == model.total_projection_years
        assert len(model.margin_schedule) == model.total_projection_years
        # capex/wc only specified in first stage - still should match
        # (with None placeholders for later years if needed)
    
    def test_stages_immutable_after_init(self):
        """
        Stages should be immutable (tuple) to prevent schedule desync.
        """
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=3, growth_rate=0.15),
            ],
            terminal_growth_rate=0.03,
        )
        
        # Stages should be a tuple, not a list
        assert isinstance(model.stages, tuple), (
            "stages should be immutable (tuple) to prevent schedule desync. "
            f"Got {type(model.stages).__name__}"
        )
    
    def test_cannot_mutate_stages(self):
        """
        Attempting to mutate stages should fail or be prevented.
        """
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("Growth", years=3, growth_rate=0.15),
            ],
            terminal_growth_rate=0.03,
        )
        
        original_years = model.total_projection_years
        
        # Tuple has no append method - raises AttributeError
        with pytest.raises(AttributeError):
            model.stages.append(GrowthStage("Extra", years=5, growth_rate=0.10))


class TestStepFunctionFade:
    """
    Tests for step function (operating leverage) fade mode.
    
    For capital-intensive businesses (airlines, manufacturers, utilities),
    margins don't fade linearly. Instead, they behave as step functions:
    - Flat at low margin while capacity is being filled
    - Jump to high margin when utilization exceeds threshold
    - Flat again until next capacity investment
    
    This models the fixed-cost leverage effect where high fixed costs
    mean operating leverage works both ways (high upside, high downside).
    """
    
    def test_fade_mode_enum_exists(self):
        """FadeMode enum should have linear and step options."""
        assert FadeMode.LINEAR.value == "linear"
        assert FadeMode.STEP.value == "step"
    
    def test_create_step_schedule_basic(self):
        """Step schedule should stay flat, then jump at threshold."""
        schedule = create_step_schedule(
            start_value=0.10,   # 10% margin initially
            end_value=0.25,     # 25% margin after step
            years=5,
            step_at_year=3,     # Step happens at year 3
        )
        
        assert len(schedule) == 5
        # Years 1-2: flat at start value
        assert schedule[0] == 0.10
        assert schedule[1] == 0.10
        # Years 3-5: jumped to end value
        assert schedule[2] == 0.25
        assert schedule[3] == 0.25
        assert schedule[4] == 0.25
    
    def test_create_step_schedule_early_step(self):
        """Step at year 1 should immediately use end value."""
        schedule = create_step_schedule(
            start_value=0.08,
            end_value=0.20,
            years=4,
            step_at_year=1,
        )
        
        # All years at end value (step at year 1 = immediate)
        assert all(v == 0.20 for v in schedule)
    
    def test_create_step_schedule_late_step(self):
        """Step at last year should stay at start until final year."""
        schedule = create_step_schedule(
            start_value=0.12,
            end_value=0.30,
            years=5,
            step_at_year=5,
        )
        
        # Years 1-4: at start value
        assert schedule[0] == 0.12
        assert schedule[1] == 0.12
        assert schedule[2] == 0.12
        assert schedule[3] == 0.12
        # Year 5: jumped to end
        assert schedule[4] == 0.30
    
    def test_growth_stage_with_step_fade_mode(self):
        """GrowthStage should support fade_mode parameter."""
        stage = GrowthStage(
            name="Capacity Fill",
            years=5,
            growth_rate=0.15,
            operating_margin=0.08,
            end_operating_margin=0.22,
            margin_fade_mode=FadeMode.STEP,
            margin_step_at_year=3,  # Margin jumps at year 3
        )
        
        assert stage.margin_fade_mode == FadeMode.STEP
        assert stage.margin_step_at_year == 3
    
    def test_step_fade_in_multi_stage_model(self):
        """MultiStageGrowthModel should respect step fade mode."""
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage(
                    name="Capacity Build",
                    years=4,
                    growth_rate=0.10,
                    operating_margin=0.05,       # Low margin while filling capacity
                    end_operating_margin=0.20,   # High margin once capacity filled
                    margin_fade_mode=FadeMode.STEP,
                    margin_step_at_year=3,       # Capacity fills in year 3
                ),
            ],
            terminal_growth_rate=0.03,
        )
        
        margins = model.margin_schedule
        assert margins is not None
        assert len(margins) == 4
        
        # Years 1-2: low margin (capacity not yet filled)
        assert margins[0] == 0.05
        assert margins[1] == 0.05
        # Years 3-4: high margin (capacity filled, operating leverage kicks in)
        assert margins[2] == 0.20
        assert margins[3] == 0.20
    
    def test_mixed_fade_modes_across_stages(self):
        """Different stages can use different fade modes."""
        model = MultiStageGrowthModel(
            stages=[
                # Stage 1: Step function (capacity build)
                GrowthStage(
                    name="Capacity Build",
                    years=3,
                    growth_rate=0.15,
                    operating_margin=0.08,
                    end_operating_margin=0.18,
                    margin_fade_mode=FadeMode.STEP,
                    margin_step_at_year=2,
                ),
                # Stage 2: Linear fade (maturity)
                GrowthStage(
                    name="Mature Fade",
                    years=3,
                    growth_rate=0.08,
                    end_growth_rate=0.04,
                    operating_margin=0.18,
                    end_operating_margin=0.15,
                    margin_fade_mode=FadeMode.LINEAR,
                ),
            ],
            terminal_growth_rate=0.03,
        )
        
        margins = model.margin_schedule
        assert margins is not None
        assert len(margins) == 6
        
        # Stage 1: step function (years 1-3)
        assert margins[0] == 0.08  # Before step
        assert margins[1] == 0.18  # After step (year 2)
        assert margins[2] == 0.18  # Still high
        
        # Stage 2: linear fade (years 4-6)
        assert margins[3] == 0.18  # Start of fade
        assert 0.15 < margins[4] < 0.18  # Mid-fade
        assert abs(margins[5] - 0.15) < 0.01  # End of fade
    
    def test_capital_intensive_model_template(self):
        """Pre-built model for capital-intensive businesses."""
        model = capital_intensive_model(
            capacity_fill_years=4,
            low_margin=0.06,
            high_margin=0.22,
            step_at_year=3,
            terminal_rate=0.025,
        )
        
        assert model.total_projection_years >= 4
        
        margins = model.margin_schedule
        assert margins is not None
        
        # Should have step behavior in early years
        assert margins[0] == 0.06  # Low margin
        assert margins[1] == 0.06  # Still low
        assert margins[2] == 0.22  # Jumped to high
    
    def test_default_fade_mode_is_linear(self):
        """If fade_mode not specified, should default to LINEAR."""
        stage = GrowthStage(
            name="Default",
            years=3,
            growth_rate=0.10,
            operating_margin=0.15,
            end_operating_margin=0.10,
            # No fade_mode specified
        )
        
        assert stage.margin_fade_mode == FadeMode.LINEAR
    
    def test_step_at_year_validation(self):
        """step_at_year should be validated to be within stage years."""
        with pytest.raises(ValueError, match="step_at_year"):
            GrowthStage(
                name="Invalid",
                years=3,
                growth_rate=0.10,
                operating_margin=0.15,
                end_operating_margin=0.25,
                margin_fade_mode=FadeMode.STEP,
                margin_step_at_year=5,  # Invalid: stage only has 3 years
            )
