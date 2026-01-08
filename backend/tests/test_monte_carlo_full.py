"""
Tests for Full-Model Monte Carlo Simulation.

Tests cover:
1. BoundedInput sampling stays within bounds
2. CorrelatedInputs produces correlated samples
3. Full MC runs with valid historical data
4. Decision metrics are calculated correctly
5. Edge cases (negative FCF, invalid scenarios)
"""
import random
import statistics
import pytest

from app.services.monte_carlo_full import (
    BoundedInput,
    CorrelatedInputs,
    FullMonteCarloResult,
    run_full_monte_carlo,
)


class TestBoundedInput:
    """Tests for BoundedInput bounded distribution."""
    
    def test_sample_stays_within_bounds(self):
        """Samples should always be within [min_val, max_val]."""
        inp = BoundedInput(
            name="growth",
            mean=0.10,
            std_dev=0.05,
            min_val=-0.05,
            max_val=0.30,
        )
        
        random.seed(42)
        samples = [inp.sample() for _ in range(1000)]
        
        assert all(-0.05 <= s <= 0.30 for s in samples)
        
    def test_samples_centered_around_mean(self):
        """Samples should be roughly centered around mean."""
        inp = BoundedInput(
            name="margin",
            mean=0.15,
            std_dev=0.03,
            min_val=0.0,
            max_val=0.40,
        )
        
        random.seed(42)
        samples = [inp.sample() for _ in range(5000)]
        sample_mean = statistics.mean(samples)
        
        # Mean should be close to 0.15 (within 0.02)
        assert abs(sample_mean - 0.15) < 0.02
        
    def test_narrow_bounds_still_works(self):
        """Should handle narrow bounds that truncate heavily."""
        inp = BoundedInput(
            name="terminal_growth",
            mean=0.025,
            std_dev=0.01,
            min_val=0.02,
            max_val=0.03,
        )
        
        random.seed(42)
        samples = [inp.sample() for _ in range(100)]
        
        assert all(0.02 <= s <= 0.03 for s in samples)


class TestCorrelatedInputs:
    """Tests for correlated sampling."""
    
    def test_uncorrelated_inputs_are_independent(self):
        """With identity correlation matrix, samples should be independent."""
        inputs = [
            BoundedInput("a", 0.5, 0.1, 0.0, 1.0),
            BoundedInput("b", 0.5, 0.1, 0.0, 1.0),
        ]
        # Identity matrix = no correlation
        corr = [[1.0, 0.0], [0.0, 1.0]]
        ci = CorrelatedInputs(inputs, corr)
        
        random.seed(42)
        samples = [ci.sample() for _ in range(1000)]
        
        # Calculate correlation
        a_vals = [s["a"] for s in samples]
        b_vals = [s["b"] for s in samples]
        
        # Should be close to 0
        correlation = _pearson_correlation(a_vals, b_vals)
        assert abs(correlation) < 0.15  # Allow some sampling noise
        
    def test_positive_correlation_produces_positive_relationship(self):
        """Positive correlation should make values move together."""
        inputs = [
            BoundedInput("growth", 0.5, 0.2, 0.0, 1.0),
            BoundedInput("capex", 0.5, 0.2, 0.0, 1.0),
        ]
        # Strong positive correlation
        corr = [[1.0, 0.7], [0.7, 1.0]]
        ci = CorrelatedInputs(inputs, corr)
        
        random.seed(42)
        samples = [ci.sample() for _ in range(2000)]
        
        growth_vals = [s["growth"] for s in samples]
        capex_vals = [s["capex"] for s in samples]
        
        correlation = _pearson_correlation(growth_vals, capex_vals)
        # Should be positive (maybe not exactly 0.7 due to truncation)
        assert correlation > 0.3
        
    def test_negative_correlation_produces_inverse_relationship(self):
        """Negative correlation should make values move inversely."""
        inputs = [
            BoundedInput("growth", 0.5, 0.2, 0.0, 1.0),
            BoundedInput("margin", 0.5, 0.2, 0.0, 1.0),
        ]
        # Negative correlation
        corr = [[1.0, -0.5], [-0.5, 1.0]]
        ci = CorrelatedInputs(inputs, corr)
        
        random.seed(42)
        samples = [ci.sample() for _ in range(2000)]
        
        growth_vals = [s["growth"] for s in samples]
        margin_vals = [s["margin"] for s in samples]
        
        correlation = _pearson_correlation(growth_vals, margin_vals)
        # Should be negative
        assert correlation < -0.2


class TestFullMonteCarloResult:
    """Tests for result computation."""
    
    def test_from_simulations_calculates_percentiles(self):
        """Should calculate correct percentiles."""
        values = list(range(1, 101))  # 1 to 100
        result = FullMonteCarloResult.from_simulations(
            values=values,
            current_price=50.0,
            iterations=100,
        )
        
        assert result.valid_simulations == 100
        assert result.percentiles["p50"] == 50  # Median
        assert result.percentiles["min"] == 1
        assert result.percentiles["max"] == 100
        
    def test_probability_metrics(self):
        """Should calculate probability thresholds correctly."""
        # 100 values: 60 above 50, 40 below
        values = list(range(1, 101))
        result = FullMonteCarloResult.from_simulations(
            values=values,
            current_price=40.0,  # 60% should be above
            iterations=100,
        )
        
        # P(IV > 40) should be ~60%
        assert 0.55 <= result.probability_positive_upside <= 0.65
        
    def test_cvar_10_is_mean_of_worst_10_percent(self):
        """CVaR 10% should be average of worst 10% outcomes."""
        values = list(range(1, 101))  # Sorted: 1-10 are worst 10%
        result = FullMonteCarloResult.from_simulations(
            values=values,
            current_price=50.0,
            iterations=100,
        )
        
        # CVaR 10% should be average of 1-10 = 5.5
        assert 4.5 <= result.cvar_10 <= 6.5
        
    def test_handles_empty_values(self):
        """Should handle case where all simulations fail."""
        result = FullMonteCarloResult.from_simulations(
            values=[],
            current_price=100.0,
            iterations=1000,
        )
        
        assert result.valid_simulations == 0
        assert result.mean == 0.0


class TestRunFullMonteCarlo:
    """Integration tests for the full Monte Carlo simulation."""
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for a company."""
        return {
            "historical_revenue": [100e9, 110e9, 120e9, 130e9, 140e9],
            "historical_ebit": [20e9, 22e9, 24e9, 26e9, 28e9],
            "historical_da": [5e9, 5.5e9, 6e9, 6.5e9, 7e9],
            "historical_capex": [8e9, 8.8e9, 9.6e9, 10.4e9, 11.2e9],
            "historical_working_capital": [10e9, 11e9, 12e9, 13e9, 14e9],
            "shares_outstanding": 5e9,
            "total_debt": 20e9,
            "cash": 30e9,
            "current_price": 30.0,
        }
    
    def test_runs_without_error(self, sample_historical_data):
        """Full MC should run without errors."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.08,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=100,
            seed=42,
        )
        
        assert result.iterations == 100
        assert result.valid_simulations > 50  # Most should be valid
        assert result.mean > 0
        
    def test_produces_reasonable_distribution(self, sample_historical_data):
        """Results should have reasonable spread."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.08,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=500,
            seed=42,
        )
        
        # Should have spread
        assert result.std_dev > 0
        assert result.percentiles["p95"] > result.percentiles["p5"]
        # Not crazy spread (sanity check)
        assert result.percentiles["p95"] < result.percentiles["p5"] * 20
        
    def test_respects_seed_for_reproducibility(self, sample_historical_data):
        """Same seed should produce same results."""
        kwargs = {
            **sample_historical_data,
            "base_growth": 0.08,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_discount_rate": 0.10,
            "base_terminal_growth": 0.03,
            "iterations": 100,
            "seed": 123,
        }
        
        result1 = run_full_monte_carlo(**kwargs)
        result2 = run_full_monte_carlo(**kwargs)
        
        assert result1.mean == result2.mean
        assert result1.percentiles["p50"] == result2.percentiles["p50"]
        
    def test_more_iterations_reduces_sampling_noise(self, sample_historical_data):
        """More iterations should produce more stable results."""
        kwargs = {
            **sample_historical_data,
            "base_growth": 0.08,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_discount_rate": 0.10,
            "base_terminal_growth": 0.03,
        }
        
        # Run twice with different seeds
        results_100 = []
        results_1000 = []
        
        for seed in [1, 2, 3]:
            r100 = run_full_monte_carlo(**kwargs, iterations=100, seed=seed)
            r1000 = run_full_monte_carlo(**kwargs, iterations=1000, seed=seed + 100)
            results_100.append(r100.mean)
            results_1000.append(r1000.mean)
        
        # 1000 iteration results should have lower variance between runs
        # This is a probabilistic test, might occasionally fail
        var_100 = statistics.variance(results_100)
        var_1000 = statistics.variance(results_1000)
        # More iterations should reduce variance (usually)
        assert var_1000 <= var_100 * 3  # Allow some noise
        
    def test_high_growth_increases_expected_value(self, sample_historical_data):
        """Higher growth assumption should increase expected value."""
        base_kwargs = {
            **sample_historical_data,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_discount_rate": 0.10,
            "base_terminal_growth": 0.03,
            "iterations": 500,
            "seed": 42,
        }
        
        low_growth = run_full_monte_carlo(**base_kwargs, base_growth=0.03)
        high_growth = run_full_monte_carlo(**base_kwargs, base_growth=0.15)
        
        assert high_growth.mean > low_growth.mean
        
    def test_high_discount_decreases_expected_value(self, sample_historical_data):
        """Higher discount rate should decrease expected value."""
        base_kwargs = {
            **sample_historical_data,
            "base_growth": 0.08,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_terminal_growth": 0.03,
            "iterations": 500,
            "seed": 42,
        }
        
        low_discount = run_full_monte_carlo(**base_kwargs, base_discount_rate=0.08)
        high_discount = run_full_monte_carlo(**base_kwargs, base_discount_rate=0.15)
        
        assert low_discount.mean > high_discount.mean
        
    def test_handles_negative_fcf_scenarios(self, sample_historical_data):
        """Should handle companies with negative margins gracefully."""
        # Set very low margin that will produce negative FCF
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.05,
            base_margin=-0.05,  # Negative margin
            base_da_ratio=0.03,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=100,
            seed=42,
        )
        
        # Should still run and produce results
        assert result.iterations == 100
        # Many simulations may be filtered out
        assert result.valid_simulations >= 0


class TestFullMonteCarloWACCFromComponents:
    """Tests for WACC calculation from components (instead of fixed discount rate)."""
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for a company."""
        return {
            "historical_revenue": [100e9, 110e9, 120e9, 130e9, 140e9],
            "historical_ebit": [20e9, 22e9, 24e9, 26e9, 28e9],
            "historical_da": [5e9, 5.5e9, 6e9, 6.5e9, 7e9],
            "historical_capex": [8e9, 8.8e9, 9.6e9, 10.4e9, 11.2e9],
            "historical_working_capital": [10e9, 11e9, 12e9, 13e9, 14e9],
            "shares_outstanding": 5e9,
            "total_debt": 20e9,
            "cash": 30e9,
            "current_price": 30.0,
        }
    
    def test_wacc_from_components_runs(self, sample_historical_data):
        """Monte Carlo should run when WACC components are provided."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.08,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_terminal_growth=0.03,
            # WACC components instead of base_discount_rate
            wacc_components={
                "risk_free_rate": 0.045,
                "beta": 1.2,
                "market_risk_premium": 0.055,
                "cost_of_debt": 0.05,
                "market_cap": 150e9,
            },
            iterations=100,
            seed=42,
        )
        
        assert result.valid_simulations > 50
        assert result.mean > 0
        
    def test_wacc_components_with_uncertainty(self, sample_historical_data):
        """WACC inputs should be sampled with their own standard deviations."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.08,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_terminal_growth=0.03,
            wacc_components={
                "risk_free_rate": 0.045,
                "beta": 1.2,
                "market_risk_premium": 0.055,
                "cost_of_debt": 0.05,
                "market_cap": 150e9,
                # Add std devs for sampling
                "beta_std": 0.2,
                "market_risk_premium_std": 0.01,
            },
            iterations=500,
            seed=42,
        )
        
        # Should have reasonable spread due to WACC uncertainty
        assert result.std_dev > 0
        
    def test_higher_beta_increases_discount_rate_lowers_value(self, sample_historical_data):
        """Higher beta → higher discount rate → lower intrinsic value."""
        base_kwargs = {
            **sample_historical_data,
            "base_growth": 0.08,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_terminal_growth": 0.03,
            "iterations": 300,
            "seed": 42,
        }
        
        low_beta = run_full_monte_carlo(
            **base_kwargs,
            wacc_components={
                "risk_free_rate": 0.045,
                "beta": 0.8,  # Low beta
                "market_risk_premium": 0.055,
                "cost_of_debt": 0.05,
                "market_cap": 150e9,
            },
        )
        
        high_beta = run_full_monte_carlo(
            **base_kwargs,
            wacc_components={
                "risk_free_rate": 0.045,
                "beta": 1.5,  # High beta
                "market_risk_premium": 0.055,
                "cost_of_debt": 0.05,
                "market_cap": 150e9,
            },
        )
        
        # Higher beta → higher WACC → lower value
        assert low_beta.mean > high_beta.mean


class TestFullMonteCarloMultiStageGrowth:
    """Tests for multi-stage growth support in Monte Carlo."""
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for a company."""
        return {
            "historical_revenue": [100e9, 110e9, 120e9, 130e9, 140e9],
            "historical_ebit": [20e9, 22e9, 24e9, 26e9, 28e9],
            "historical_da": [5e9, 5.5e9, 6e9, 6.5e9, 7e9],
            "historical_capex": [8e9, 8.8e9, 9.6e9, 10.4e9, 11.2e9],
            "historical_working_capital": [10e9, 11e9, 12e9, 13e9, 14e9],
            "shares_outstanding": 5e9,
            "total_debt": 20e9,
            "cash": 30e9,
            "current_price": 30.0,
        }
    
    def test_multi_stage_growth_runs(self, sample_historical_data):
        """Monte Carlo should run with multi-stage growth."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            # Multi-stage growth instead of single base_growth
            growth_stages=[
                {"name": "High Growth", "years": 3, "growth_rate": 0.20},
                {"name": "Fade", "years": 3, "growth_rate": 0.20, "end_growth_rate": 0.08},
                {"name": "Mature", "years": 4, "growth_rate": 0.05},
            ],
            iterations=100,
            seed=42,
        )
        
        assert result.valid_simulations > 50
        assert result.mean > 0
        
    def test_multi_stage_with_uncertainty(self, sample_historical_data):
        """Growth stage rates should be sampled with uncertainty."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            growth_stages=[
                {"name": "High", "years": 3, "growth_rate": 0.15, "growth_std": 0.05},
                {"name": "Mature", "years": 7, "growth_rate": 0.05, "growth_std": 0.02},
            ],
            iterations=300,
            seed=42,
        )
        
        assert result.std_dev > 0
        
    def test_high_growth_stage_increases_value(self, sample_historical_data):
        """Multi-stage with high initial growth should produce higher values."""
        base_kwargs = {
            **sample_historical_data,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_discount_rate": 0.10,
            "base_terminal_growth": 0.03,
            "iterations": 300,
            "seed": 42,
        }
        
        low_growth = run_full_monte_carlo(
            **base_kwargs,
            growth_stages=[
                {"name": "Slow", "years": 5, "growth_rate": 0.05},
                {"name": "Mature", "years": 5, "growth_rate": 0.03},
            ],
        )
        
        high_growth = run_full_monte_carlo(
            **base_kwargs,
            growth_stages=[
                {"name": "Fast", "years": 5, "growth_rate": 0.25},
                {"name": "Mature", "years": 5, "growth_rate": 0.05},
            ],
        )
        
        assert high_growth.mean > low_growth.mean


class TestFullMonteCarloMidYearDiscounting:
    """Tests for mid-year discounting option."""
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for a company."""
        return {
            "historical_revenue": [100e9, 110e9, 120e9, 130e9, 140e9],
            "historical_ebit": [20e9, 22e9, 24e9, 26e9, 28e9],
            "historical_da": [5e9, 5.5e9, 6e9, 6.5e9, 7e9],
            "historical_capex": [8e9, 8.8e9, 9.6e9, 10.4e9, 11.2e9],
            "historical_working_capital": [10e9, 11e9, 12e9, 13e9, 14e9],
            "shares_outstanding": 5e9,
            "total_debt": 20e9,
            "cash": 30e9,
            "current_price": 30.0,
        }
    
    def test_mid_year_discounting_runs(self, sample_historical_data):
        """Monte Carlo should run with mid-year discounting enabled."""
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.08,
            base_margin=0.20,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            use_mid_year_discounting=True,
            iterations=100,
            seed=42,
        )
        
        assert result.valid_simulations > 50
        assert result.mean > 0
        
    def test_mid_year_discounting_increases_value(self, sample_historical_data):
        """Mid-year discounting should produce higher values (cash received sooner)."""
        base_kwargs = {
            **sample_historical_data,
            "base_growth": 0.08,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_discount_rate": 0.10,
            "base_terminal_growth": 0.03,
            "iterations": 300,
            "seed": 42,
        }
        
        end_year = run_full_monte_carlo(**base_kwargs, use_mid_year_discounting=False)
        mid_year = run_full_monte_carlo(**base_kwargs, use_mid_year_discounting=True)
        
        # Mid-year should be higher (cash flows discounted less)
        assert mid_year.mean > end_year.mean
        
    def test_mid_year_effect_larger_at_high_discount(self, sample_historical_data):
        """Mid-year effect should be more pronounced at higher discount rates."""
        base_kwargs = {
            **sample_historical_data,
            "base_growth": 0.08,
            "base_margin": 0.20,
            "base_da_ratio": 0.05,
            "base_capex_ratio": 0.08,
            "base_wc_ratio": 0.10,
            "base_tax_rate": 0.25,
            "base_terminal_growth": 0.03,
            "iterations": 300,
            "seed": 42,
        }
        
        # Low discount rate (5%)
        low_discount_end = run_full_monte_carlo(
            **base_kwargs, base_discount_rate=0.05, use_mid_year_discounting=False
        )
        low_discount_mid = run_full_monte_carlo(
            **base_kwargs, base_discount_rate=0.05, use_mid_year_discounting=True
        )
        low_discount_diff = (low_discount_mid.mean - low_discount_end.mean) / low_discount_end.mean
        
        # High discount rate (15%)
        high_discount_end = run_full_monte_carlo(
            **base_kwargs, base_discount_rate=0.15, use_mid_year_discounting=False
        )
        high_discount_mid = run_full_monte_carlo(
            **base_kwargs, base_discount_rate=0.15, use_mid_year_discounting=True
        )
        high_discount_diff = (high_discount_mid.mean - high_discount_end.mean) / high_discount_end.mean
        
        # Effect should be larger at high discount rates
        assert high_discount_diff > low_discount_diff


class TestWACCComponentsWithoutSampling:
    """Tests for Bug 1: WACC components without sampling std devs."""
    
    def test_wacc_components_without_std_uses_fixed_wacc(self):
        """
        When WACC components are provided without beta_std or mrp_std,
        the simulation should use the fixed computed WACC, NOT sample it.
        
        Bug: Without std devs, the code was adding a 'discount' input for
        sampling which introduced variance when there should be none.
        """
        random.seed(42)
        
        # Provide WACC components WITHOUT any std devs (fixed WACC scenario)
        wacc_components = {
            "risk_free_rate": 0.04,
            "beta": 1.0,
            "market_risk_premium": 0.06,
            "cost_of_debt": 0.05,
            "market_cap": 100e9,
            # No beta_std or market_risk_premium_std
        }
        
        # Run with VERY low discount_std to verify it's not being used
        result = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[10e9, 11e9, 12e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_da_ratio=0.02,
            base_capex_ratio=0.035,
            base_wc_ratio=0.12,
            base_discount_rate=0.10,  # This should be IGNORED when wacc_components provided
            base_terminal_growth=0.025,
            growth_std=0.0,  # No sampling variance
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.05,  # This should be IGNORED when wacc_components provided
            terminal_growth_std=0.0,
            projection_years=10,
            iterations=100,
            wacc_components=wacc_components,
            growth_stages=[{"name": "Stable", "years": 10, "growth_rate": 0.05}],
        )
        
        # With zero variance in all inputs except discount_std (which should be ignored),
        # all iterations should produce the SAME per-share value
        # If discount_std is incorrectly applied, values will vary significantly
        assert result.std_dev < 1.0, (
            f"Std dev ({result.std_dev:.2f}) too high - discount sampling is being incorrectly applied "
            f"when WACC components are provided without sampling std devs"
        )


class TestWorkingCapitalWithEmptyHistory:
    """Tests for Bug 2: Empty historical_working_capital handling."""
    
    def test_empty_wc_history_uses_revenue_based_baseline(self):
        """
        When historical_working_capital is empty, year 0's delta_wc should
        be calculated using historical_revenue[-1] * wc_ratio as the baseline,
        NOT current_revenue * wc_ratio (which would make delta_wc = 0).
        
        Bug: When WC history is empty, prev_wc was set to current_revenue * wc_ratio,
        making delta_wc = wc - wc = 0, which overstates FCF.
        """
        random.seed(42)
        
        # Use high WC ratio and growth to make the bug more visible
        # With 20% WC ratio and 10% growth:
        # - Historical baseline WC: 100e9 * 0.20 = 20e9
        # - Y1 projected WC: 110e9 * 0.20 = 22e9
        # - Correct delta_wc Y1: 22e9 - 20e9 = 2e9 (reduces FCF)
        # - Bug delta_wc Y1: 22e9 - 22e9 = 0 (no WC drain, inflates FCF)
        
        # Run with empty WC history
        result_empty_wc = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[],  # Empty WC history
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_da_ratio=0.02,
            base_capex_ratio=0.035,
            base_wc_ratio=0.20,  # High WC ratio to amplify bug
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            projection_years=10,
            iterations=100,
            growth_stages=[{"name": "High Growth", "years": 10, "growth_rate": 0.10}],  # High growth
        )
        
        # Run with explicit WC history matching historical_revenue * wc_ratio
        result_explicit_wc = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[18e9, 19e9, 20e9],  # 20% of revenue
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_da_ratio=0.02,
            base_capex_ratio=0.035,
            base_wc_ratio=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            projection_years=10,
            iterations=100,
            growth_stages=[{"name": "High Growth", "years": 10, "growth_rate": 0.10}],
        )
        
        # Values should be essentially identical if empty WC is handled correctly
        # (both use 20% of historical revenue as baseline)
        pct_diff = abs(result_empty_wc.mean - result_explicit_wc.mean) / result_explicit_wc.mean
        
        assert pct_diff < 0.01, (  # Tighter tolerance: 1%
            f"Empty WC history gives {result_empty_wc.mean:.2f}, "
            f"explicit WC gives {result_explicit_wc.mean:.2f} "
            f"(diff: {pct_diff*100:.1f}%). "
            f"Empty WC should match explicit WC baseline."
        )


# Helper function for correlation calculation
def _pearson_correlation(x: list, y: list) -> float:
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
    denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
    
    if denom_x == 0 or denom_y == 0:
        return 0.0
    
    return numerator / (denom_x * denom_y)
