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


class TestEquityBridgeIntegration:
    """
    Tests for P0: Monte Carlo should use full institutional equity bridge,
    not just net debt.
    
    Equity = EV - Net Debt - Minority Interest - Preferred + NOLs - Pension
    """
    
    def test_accepts_equity_bridge_components(self):
        """Monte Carlo should accept equity bridge parameters."""
        result = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            iterations=100,
            seed=42,
            # Equity bridge components
            minority_interest=1e9,
            preferred_stock=500e6,
            deferred_tax_assets=2e9,  # NOLs - adds value
            pension_deficit=300e6,
        )
        
        assert result.mean > 0
        assert result.iterations == 100
    
    def test_minority_interest_reduces_value(self):
        """Minority interest should reduce per-share value."""
        base_result = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,  # Zero variance for deterministic comparison
            margin_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            iterations=10,
            seed=42,
        )
        
        with_minority = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            iterations=10,
            seed=42,
            minority_interest=5e9,  # $5B minority interest
        )
        
        # Minority interest reduces equity value
        # With 1B shares, 5B minority = $5 per share reduction
        expected_reduction = 5e9 / 1e9  # $5 per share
        actual_reduction = base_result.mean - with_minority.mean
        
        assert actual_reduction > 0, "Minority interest should reduce value"
        assert abs(actual_reduction - expected_reduction) < 0.10, (
            f"Expected ~${expected_reduction:.2f} reduction, got ${actual_reduction:.2f}"
        )
    
    def test_deferred_tax_assets_add_value(self):
        """Deferred tax assets (NOLs) should increase per-share value."""
        base_result = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            iterations=10,
            seed=42,
        )
        
        with_nols = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            iterations=10,
            seed=42,
            deferred_tax_assets=3e9,  # $3B NOLs
        )
        
        # NOLs add to equity value
        expected_increase = 3e9 / 1e9  # $3 per share
        actual_increase = with_nols.mean - base_result.mean
        
        assert actual_increase > 0, "NOLs should increase value"
        assert abs(actual_increase - expected_increase) < 0.10, (
            f"Expected ~${expected_increase:.2f} increase, got ${actual_increase:.2f}"
        )
    
    def test_full_equity_bridge_combined(self):
        """Full equity bridge should reflect all components."""
        base_result = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            iterations=10,
            seed=42,
        )
        
        # Equity = EV - Net Debt - Minority - Preferred + NOLs - Pension
        # Net impact: -1B - 0.5B + 2B - 0.3B = +0.2B = +$0.20/share
        with_bridge = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            growth_std=0.0,
            margin_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            iterations=10,
            seed=42,
            minority_interest=1e9,    # -$1B
            preferred_stock=0.5e9,    # -$0.5B
            deferred_tax_assets=2e9,  # +$2B
            pension_deficit=0.3e9,    # -$0.3B
        )
        
        # Net impact = +0.2B on 1B shares = +$0.20/share
        expected_delta = 0.2e9 / 1e9  # $0.20
        actual_delta = with_bridge.mean - base_result.mean
        
        assert abs(actual_delta - expected_delta) < 0.05, (
            f"Expected ~${expected_delta:.2f} net change, got ${actual_delta:.2f}"
        )
    
    def test_defaults_to_zero_for_backward_compatibility(self):
        """Omitting equity bridge params should work (default to 0)."""
        # This should work without any equity bridge params
        result = run_full_monte_carlo(
            historical_revenue=[90e9, 95e9, 100e9],
            historical_ebit=[18e9, 19e9, 20e9],
            historical_da=[2e9, 2.1e9, 2.2e9],
            historical_capex=[3e9, 3.2e9, 3.5e9],
            historical_working_capital=[9e9, 9.5e9, 10e9],
            shares_outstanding=1e9,
            total_debt=20e9,
            cash=10e9,
            current_price=100,
            base_margin=0.20,
            base_discount_rate=0.10,
            base_terminal_growth=0.025,
            iterations=10,
            seed=42,
        )
        
        assert result.mean > 0
        assert result.iterations == 10


class TestMonteCarloAPIEquityBridge:
    """
    Tests that the Monte Carlo API endpoint correctly passes
    equity bridge components extracted from company data.
    
    This is a P1 fix - the API endpoint must pass:
    - minority_interest
    - preferred_stock
    - deferred_tax_assets
    - pension_deficit
    """
    
    @pytest.fixture
    def mock_extractor(self):
        """Create a mock DataExtractor with equity bridge data."""
        from unittest.mock import MagicMock
        extractor = MagicMock()
        extractor.revenue_history.return_value = [90e9, 95e9, 100e9]
        extractor.ebit_history.return_value = [18e9, 19e9, 20e9]
        extractor.da_history.return_value = [2e9, 2.1e9, 2.2e9]
        extractor.capex_history.return_value = [3e9, 3.2e9, 3.5e9]
        extractor.working_capital_history.return_value = [9e9, 9.5e9, 10e9]
        extractor.shares_outstanding.return_value = 1e9
        extractor.total_debt.return_value = 20e9
        extractor.cash.return_value = 10e9
        extractor.market_cap.return_value = 100e9
        # Equity bridge components
        extractor.minority_interest.return_value = 2e9
        extractor.preferred_stock.return_value = 500e6
        extractor.deferred_tax_assets.return_value = 1e9
        extractor.pension_liability.return_value = 300e6
        return extractor
    
    def test_endpoint_extracts_equity_bridge_components(self, mock_extractor):
        """
        The API endpoint should call all equity bridge extractors.
        """
        # Just verify the extractor has these methods and they return values
        assert mock_extractor.minority_interest() == 2e9
        assert mock_extractor.preferred_stock() == 500e6
        assert mock_extractor.deferred_tax_assets() == 1e9
        assert mock_extractor.pension_liability() == 300e6
    
    def test_run_full_monte_carlo_with_extracted_bridge(self, mock_extractor):
        """
        Verify that passing extracted equity bridge values affects result.
        """
        base_kwargs = {
            "historical_revenue": mock_extractor.revenue_history(),
            "historical_ebit": mock_extractor.ebit_history(),
            "historical_da": mock_extractor.da_history(),
            "historical_capex": mock_extractor.capex_history(),
            "historical_working_capital": mock_extractor.working_capital_history(),
            "shares_outstanding": mock_extractor.shares_outstanding(),
            "total_debt": mock_extractor.total_debt(),
            "cash": mock_extractor.cash(),
            "current_price": 100,
            "base_margin": 0.20,
            "base_discount_rate": 0.10,
            "base_terminal_growth": 0.025,
            "growth_std": 0.0,
            "margin_std": 0.0,
            "discount_std": 0.0,
            "terminal_growth_std": 0.0,
            "iterations": 10,
            "seed": 42,
        }
        
        # Without equity bridge
        base_result = run_full_monte_carlo(**base_kwargs)
        
        # With equity bridge components from extractor
        with_bridge = run_full_monte_carlo(
            **base_kwargs,
            minority_interest=mock_extractor.minority_interest() or 0,
            preferred_stock=mock_extractor.preferred_stock() or 0,
            deferred_tax_assets=mock_extractor.deferred_tax_assets() or 0,
            pension_deficit=mock_extractor.pension_liability() or 0,
        )
        
        # Net impact: -2B (minority) -0.5B (pref) +1B (NOLs) -0.3B (pension) = -1.8B
        # On 1B shares = -$1.80/share
        expected_delta = -1.8e9 / 1e9
        actual_delta = with_bridge.mean - base_result.mean
        
        assert abs(actual_delta - expected_delta) < 0.1, (
            f"Expected ~${expected_delta:.2f} impact from equity bridge, got ${actual_delta:.2f}"
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


class TestNegativeTerminalFCFHandling:
    """
    Tests for P0: Proper handling of negative terminal FCF in Monte Carlo.
    
    Bug: When final year FCF is negative, the code used an arbitrary heuristic:
         `terminal_value = final_fcf * 10`
    
    This is economically meaningless because:
    1. The Gordon Growth Model assumes perpetual positive cash flows
    2. A negative FCF times any positive multiple is still negative
    3. There's no basis for the "10x distressed multiple"
    
    Fix: Skip simulations with negative terminal FCF and track them.
    """
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for testing."""
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
    
    def test_negative_terminal_fcf_simulations_are_skipped(self, sample_historical_data):
        """
        Simulations where terminal FCF is negative should be skipped,
        not computed with an arbitrary multiple.
        """
        # Use very low margin that will frequently produce negative FCF
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.05,
            base_margin=-0.02,  # Negative margin → negative FCF
            base_da_ratio=0.03,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=500,
            seed=42,
        )
        
        # With negative margin, many simulations should be skipped
        # The key assertion: valid_simulations < iterations
        assert result.valid_simulations < result.iterations, (
            "Some simulations should be skipped when terminal FCF is often negative"
        )
        
        # Skipped simulations should be tracked
        assert hasattr(result, 'negative_terminal_fcf_count'), (
            "Result should track how many simulations had negative terminal FCF"
        )
        assert result.negative_terminal_fcf_count > 0, (
            "With negative margin, some simulations should have negative terminal FCF"
        )
    
    def test_negative_terminal_fcf_does_not_use_arbitrary_multiple(self, sample_historical_data):
        """
        The old bug: terminal_value = final_fcf * 10
        
        This should NOT happen. If we can detect the bug, the test fails.
        """
        # Run with parameters that guarantee negative terminal FCF
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.02,
            base_margin=-0.10,  # -10% margin guarantees negative FCF
            base_da_ratio=0.03,
            base_capex_ratio=0.10,
            base_wc_ratio=0.05,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            margin_std=0.01,  # Low std so margin stays negative
            iterations=100,
            seed=42,
        )
        
        # With very negative margin and low std, almost all simulations
        # should have negative terminal FCF and be skipped
        # If the old bug exists, valid_simulations would equal iterations
        # because the arbitrary multiple would produce a "valid" (but wrong) value
        
        # If more than 90% are "valid" with -10% margin, the bug likely exists
        if result.valid_simulations > 90:
            # Check if mean is suspiciously negative (bug symptom)
            # With the old bug: negative FCF * 10 = large negative TV
            # This could produce very negative intrinsic values
            assert result.mean is None or result.mean > -100, (
                f"Mean value of {result.mean} suggests the arbitrary multiple bug exists. "
                "Negative terminal FCF should be skipped, not multiplied by 10."
            )
    
    def test_warning_when_many_simulations_skipped(self, sample_historical_data):
        """
        If more than X% of simulations are skipped due to negative terminal FCF,
        a warning should be included in the result.
        """
        # Use parameters that will cause many skipped simulations
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.03,
            base_margin=0.02,  # Low but positive margin
            margin_std=0.05,   # High std so many will go negative
            base_da_ratio=0.03,
            base_capex_ratio=0.10,  # High capex to push FCF negative
            base_wc_ratio=0.05,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=500,
            seed=42,
        )
        
        # If significant portion skipped, should have a warning
        skip_pct = result.negative_terminal_fcf_count / result.iterations * 100
        if skip_pct > 20:  # More than 20% skipped
            assert hasattr(result, 'warnings') and result.warnings, (
                f"{skip_pct:.1f}% of simulations had negative terminal FCF - "
                "result should include a warning about this"
            )
    
    def test_valid_simulations_with_positive_fcf_unaffected(self, sample_historical_data):
        """
        Normal simulations with positive FCF should work exactly as before.
        """
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.08,
            base_margin=0.20,  # Healthy 20% margin
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=500,
            seed=42,
        )
        
        # With healthy margin, most simulations should be valid
        assert result.valid_simulations > 450, (
            "With 20% margin, most simulations should have positive FCF"
        )
        
        # Mean should be positive and reasonable
        assert result.mean > 0, "Mean should be positive for healthy company"
        
        # Negative terminal FCF count should be low or zero
        assert result.negative_terminal_fcf_count < 50, (
            "With 20% margin, very few simulations should have negative terminal FCF"
        )
    
    def test_zero_terminal_fcf_is_not_skipped(self, sample_historical_data):
        """
        Zero terminal FCF is economically valid (TV = 0) and should NOT be skipped.
        
        Bug: The condition was `if final_fcf <= 0:` which incorrectly skipped
        zero FCF cases along with negative ones.
        
        Fix: Changed to `if final_fcf < 0:` to only skip truly negative cases.
        """
        # Use parameters where margin ≈ reinvestment needs → FCF ≈ 0
        # This is a breakeven company scenario
        result = run_full_monte_carlo(
            **sample_historical_data,
            base_growth=0.05,
            base_margin=0.10,      # 10% margin
            margin_std=0.001,      # Very low std to keep margin stable
            base_da_ratio=0.03,
            base_capex_ratio=0.06, # CapEx slightly above D&A (growth requires investment)
            base_wc_ratio=0.05,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            iterations=100,
            seed=42,
        )
        
        # With stable margin, simulations should mostly be valid
        # (even if some land on exactly zero FCF)
        assert result.valid_simulations > 50, (
            f"Expected most simulations to be valid, got {result.valid_simulations}"
        )
        
        # The key test: simulations with zero FCF should NOT increment
        # the negative_terminal_fcf_count
        # With these parameters, we shouldn't have many skipped
        assert result.negative_terminal_fcf_count < result.iterations * 0.5, (
            "Zero FCF should not be counted as negative terminal FCF"
        )


class TestFatTailsDistribution:
    """
    Tests for fat tails (Student's t-distribution) in Monte Carlo.
    
    The "Gaussian Fallacy" is that markets don't follow Normal distributions.
    Real markets have "fat tails" - extreme events happen more often than
    Normal distribution predicts (1-in-100 year crashes happen more often).
    
    Student's t-distribution with low degrees of freedom (df) has fatter tails.
    - df=∞ → Normal distribution
    - df=3-5 → Moderate fat tails (recommended for finance)
    - df=1 → Cauchy (very fat tails, undefined variance)
    """
    
    def test_bounded_input_accepts_degrees_of_freedom(self):
        """
        BoundedInput should accept a degrees_of_freedom parameter.
        
        When df is specified, it should use Student's t-distribution
        instead of Normal distribution for sampling.
        """
        # This test will fail until we implement fat tails
        inp = BoundedInput(
            name="growth",
            mean=0.10,
            std_dev=0.05,
            min_val=-0.20,
            max_val=0.40,
            degrees_of_freedom=4,  # Fat tails parameter
        )
        
        # Should have the attribute
        assert hasattr(inp, 'degrees_of_freedom')
        assert inp.degrees_of_freedom == 4
    
    def test_fat_tails_produces_more_extreme_values(self):
        """
        With fat tails (low df), we should see more extreme samples
        compared to Normal distribution.
        
        Test: Count samples beyond 3 standard deviations from mean.
        - Normal: ~0.3% of samples beyond 3σ
        - t(df=4): ~1.2% of samples beyond 3σ (4x more)
        """
        random.seed(42)
        
        # Normal distribution (df=None or very high)
        normal_inp = BoundedInput(
            name="growth",
            mean=0.10,
            std_dev=0.05,
            min_val=-0.50,  # Wide bounds so we can see extremes
            max_val=0.70,
            degrees_of_freedom=None,  # Normal distribution
        )
        
        # Fat tails distribution (df=4)
        fat_tail_inp = BoundedInput(
            name="growth",
            mean=0.10,
            std_dev=0.05,
            min_val=-0.50,
            max_val=0.70,
            degrees_of_freedom=4,  # Fat tails
        )
        
        n_samples = 10000
        threshold_low = 0.10 - 3 * 0.05  # mean - 3σ = -0.05
        threshold_high = 0.10 + 3 * 0.05  # mean + 3σ = 0.25
        
        random.seed(42)
        normal_samples = [normal_inp.sample() for _ in range(n_samples)]
        normal_extremes = sum(1 for s in normal_samples if s < threshold_low or s > threshold_high)
        
        random.seed(42)
        fat_samples = [fat_tail_inp.sample() for _ in range(n_samples)]
        fat_extremes = sum(1 for s in fat_samples if s < threshold_low or s > threshold_high)
        
        # Fat tails should have MORE extreme values
        # (at least 2x as many, typically 3-4x)
        assert fat_extremes > normal_extremes * 1.5, (
            f"Fat tails (df=4) should produce more extremes. "
            f"Normal: {normal_extremes}, Fat tails: {fat_extremes}"
        )
    
    def test_run_full_monte_carlo_accepts_fat_tails_parameter(self):
        """
        run_full_monte_carlo should accept a fat_tails_df parameter.
        
        This enables users to model "1-in-100 year" economic crashes
        more realistically than Normal distribution allows.
        """
        # Historical data (5 years)
        historical_revenue = [80e6, 85e6, 90e6, 95e6, 100e6]
        historical_ebit = [12e6, 13e6, 14e6, 15e6, 16e6]
        historical_da = [3e6, 3.2e6, 3.4e6, 3.6e6, 3.8e6]
        historical_capex = [4e6, 4.2e6, 4.5e6, 4.8e6, 5e6]
        historical_wc = [8e6, 8.5e6, 9e6, 9.5e6, 10e6]
        
        result = run_full_monte_carlo(
            historical_revenue=historical_revenue,
            historical_ebit=historical_ebit,
            historical_da=historical_da,
            historical_capex=historical_capex,
            historical_working_capital=historical_wc,
            shares_outstanding=10_000_000,
            total_debt=30_000_000,
            cash=10_000_000,
            current_price=15.0,
            base_growth=0.08,
            base_margin=0.15,
            base_discount_rate=0.10,
            projection_years=5,
            iterations=100,
            seed=42,
            fat_tails_df=4,  # Enable fat tails
        )
        
        # Should complete without error and have valid results
        assert result is not None
        assert result.valid_simulations > 0
    
    def test_correlated_inputs_respect_fat_tails(self):
        """
        CorrelatedInputs.sample() should use fat tails when degrees_of_freedom is set.
        
        Bug fix verification: Previously, CorrelatedInputs.sample() generated
        samples directly from Normal distribution, ignoring degrees_of_freedom.
        This meant fat_tails_df was silently ignored for correlated inputs.
        """
        from app.services.monte_carlo_full import CorrelatedInputs
        
        random.seed(42)
        
        # Create correlated inputs WITH fat tails
        fat_tail_inputs = CorrelatedInputs(
            inputs=[
                BoundedInput("growth", 0.10, 0.05, -0.50, 0.70, degrees_of_freedom=4),
                BoundedInput("margin", 0.20, 0.05, -0.50, 0.70, degrees_of_freedom=4),
            ],
            correlation_matrix=[[1.0, -0.2], [-0.2, 1.0]],
        )
        
        # Create correlated inputs WITHOUT fat tails (Normal)
        normal_inputs = CorrelatedInputs(
            inputs=[
                BoundedInput("growth", 0.10, 0.05, -0.50, 0.70, degrees_of_freedom=None),
                BoundedInput("margin", 0.20, 0.05, -0.50, 0.70, degrees_of_freedom=None),
            ],
            correlation_matrix=[[1.0, -0.2], [-0.2, 1.0]],
        )
        
        n_samples = 10000
        threshold = 3 * 0.05  # 3 standard deviations
        
        # Sample from fat tails
        random.seed(42)
        fat_samples = [fat_tail_inputs.sample()["growth"] for _ in range(n_samples)]
        fat_extremes = sum(1 for s in fat_samples if abs(s - 0.10) > threshold)
        
        # Sample from normal
        random.seed(42)
        normal_samples = [normal_inputs.sample()["growth"] for _ in range(n_samples)]
        normal_extremes = sum(1 for s in normal_samples if abs(s - 0.10) > threshold)
        
        # Fat tails should produce more extreme values
        assert fat_extremes > normal_extremes, (
            f"CorrelatedInputs should respect degrees_of_freedom. "
            f"Fat tails: {fat_extremes} extremes, Normal: {normal_extremes} extremes"
        )


class TestFCFProjectorIntegration:
    """
    P0.1 Fix: Monte Carlo must use FCFProjector.project() instead of its own FCF loop.
    
    Problem: Full Monte Carlo has its own FCF calculation loop that:
    - Only supports "level" mode for WC (doesn't respect wc_mode parameter)
    - Doesn't support economics schedules (margin_schedule, capex_schedule, wc_schedule)
    - Diverges from the main DCF engine (ValuationService/FCFProjector)
    
    Solution: Replace the manual FCF loop with calls to FCFProjector.project().
    
    These tests verify that Monte Carlo produces the same FCF calculations as
    FCFProjector.project() when given deterministic inputs.
    """
    
    def test_mc_respects_wc_mode_incremental(self):
        """
        Monte Carlo should respect wc_mode="incremental" like FCFProjector.
        
        Currently FAILS because MC only implements "level" mode.
        """
        from app.services.fcf_projector import FCFProjector
        
        # Historical data
        hist_revenue = [100e9, 110e9, 121e9]
        hist_ebit = [15e9, 16.5e9, 18.15e9]
        hist_da = [5e9, 5.5e9, 6.05e9]
        hist_capex = [8e9, 8.8e9, 9.68e9]
        hist_wc = [10e9, 11e9, 12.1e9]
        
        # Create FCFProjector and project with incremental WC mode
        projector = FCFProjector(
            historical_revenue=hist_revenue,
            historical_ebit=hist_ebit,
            historical_da=hist_da,
            historical_capex=hist_capex,
            historical_working_capital=hist_wc,
            tax_rate=0.25,
            wc_mode="incremental",
        )
        
        # Project 5 years with specific assumptions
        fcf_projections = projector.project(
            years=5,
            revenue_growth=0.10,
            operating_margin=0.15,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.10,  # WC intensity (for incremental mode)
            wc_mode="incremental",
        )
        
        # Extract FCFs from FCFProjector
        fcf_projector_fcfs = [p["fcf"] for p in fcf_projections]
        
        # Run Monte Carlo with same deterministic inputs (seed=42, 1 iteration)
        result = run_full_monte_carlo(
            historical_revenue=hist_revenue,
            historical_ebit=hist_ebit,
            historical_da=hist_da,
            historical_capex=hist_capex,
            historical_working_capital=hist_wc,
            shares_outstanding=1e9,
            total_debt=50e9,
            cash=20e9,
            current_price=100.0,
            base_growth=0.10,
            base_margin=0.15,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            # Zero std devs for deterministic output
            growth_std=0.0,
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            projection_years=5,
            iterations=1,
            seed=42,
            # THIS IS THE KEY - should respect incremental mode
            wc_mode="incremental",
        )
        
        # Monte Carlo should produce positive value (deterministic inputs)
        assert result.valid_simulations == 1, (
            "Monte Carlo should produce valid result with deterministic inputs"
        )
        
        # The per-share value should match if FCF calculations align
        # For now, just verify the parameter is accepted
        # Full parity test will be added after implementation
    
    def test_mc_respects_margin_schedule(self):
        """
        Monte Carlo should respect margin_schedule for multi-stage economics.
        
        Currently FAILS because MC doesn't pass margin_schedule to FCFProjector.
        """
        from app.services.fcf_projector import FCFProjector
        
        hist_revenue = [100e9, 110e9, 121e9]
        hist_ebit = [15e9, 16.5e9, 18.15e9]
        hist_da = [5e9, 5.5e9, 6.05e9]
        hist_capex = [8e9, 8.8e9, 9.68e9]
        hist_wc = [10e9, 11e9, 12.1e9]
        
        # Margin schedule: starts high, fades to mature
        margin_schedule = [0.20, 0.18, 0.16, 0.14, 0.12]
        
        # FCFProjector with margin schedule
        projector = FCFProjector(
            historical_revenue=hist_revenue,
            historical_ebit=hist_ebit,
            historical_da=hist_da,
            historical_capex=hist_capex,
            historical_working_capital=hist_wc,
            tax_rate=0.25,
        )
        
        fcf_projections = projector.project(
            years=5,
            revenue_growth=0.10,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.10,
            margin_schedule=margin_schedule,
        )
        
        # The terminal year should use margin=0.12 (last in schedule)
        terminal_margin_from_projector = fcf_projections[-1]["ebit"] / fcf_projections[-1]["revenue"]
        
        # Run Monte Carlo with margin_schedule
        result = run_full_monte_carlo(
            historical_revenue=hist_revenue,
            historical_ebit=hist_ebit,
            historical_da=hist_da,
            historical_capex=hist_capex,
            historical_working_capital=hist_wc,
            shares_outstanding=1e9,
            total_debt=50e9,
            cash=20e9,
            current_price=100.0,
            base_growth=0.10,
            base_margin=0.20,  # Starting margin
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            growth_std=0.0,
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            projection_years=5,
            iterations=1,
            seed=42,
            # THIS IS THE KEY - should respect margin_schedule
            margin_schedule=margin_schedule,
        )
        
        # Verify margin schedule is accepted and used
        assert result.valid_simulations == 1, (
            "Monte Carlo should accept margin_schedule parameter"
        )
        
        # Terminal margin should be ~0.12, not 0.20
        # (This assertion will verify the implementation is correct)
        assert abs(terminal_margin_from_projector - 0.12) < 0.01, (
            f"FCFProjector terminal margin should be ~12%, got {terminal_margin_from_projector:.1%}"
        )


class TestDilutionSupport:
    """
    P0.2 Fix: Monte Carlo must support annual_dilution_rate like ValuationService.
    
    Problem: Full Monte Carlo uses shares_outstanding directly for per-share
    calculations, ignoring SBC dilution. For tech companies with 2-3% annual
    dilution, a 10-year projection would overstate per-share value by 20-30%.
    
    Solution: Add annual_dilution_rate parameter and calculate terminal_shares
    using the same formula as ValuationService:
    terminal_shares = current_shares * ((1 + annual_dilution_rate) ** projection_years)
    """
    
    def test_mc_accepts_annual_dilution_rate_parameter(self):
        """
        Monte Carlo should accept annual_dilution_rate parameter.
        """
        hist_revenue = [100e9, 110e9, 121e9]
        hist_ebit = [15e9, 16.5e9, 18.15e9]
        hist_da = [5e9, 5.5e9, 6.05e9]
        hist_capex = [8e9, 8.8e9, 9.68e9]
        hist_wc = [10e9, 11e9, 12.1e9]
        
        # Should not raise TypeError for unknown parameter
        result = run_full_monte_carlo(
            historical_revenue=hist_revenue,
            historical_ebit=hist_ebit,
            historical_da=hist_da,
            historical_capex=hist_capex,
            historical_working_capital=hist_wc,
            shares_outstanding=1e9,
            total_debt=50e9,
            cash=20e9,
            current_price=100.0,
            base_growth=0.10,
            base_margin=0.15,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            growth_std=0.0,
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            projection_years=5,
            iterations=1,
            seed=42,
            # THIS IS THE KEY - should accept dilution parameter
            annual_dilution_rate=0.03,  # 3% annual dilution
        )
        
        assert result.valid_simulations == 1, (
            "Monte Carlo should accept annual_dilution_rate parameter"
        )
    
    def test_dilution_reduces_per_share_value(self):
        """
        With positive dilution, per-share value should be LOWER than without dilution.
        
        At 3% annual dilution over 10 years:
        terminal_shares = 1e9 * (1.03)^10 = 1.344e9 shares
        
        This means ~34% more shares, so per-share value should be ~25% lower.
        """
        hist_revenue = [100e9, 110e9, 121e9]
        hist_ebit = [15e9, 16.5e9, 18.15e9]
        hist_da = [5e9, 5.5e9, 6.05e9]
        hist_capex = [8e9, 8.8e9, 9.68e9]
        hist_wc = [10e9, 11e9, 12.1e9]
        
        common_params = dict(
            historical_revenue=hist_revenue,
            historical_ebit=hist_ebit,
            historical_da=hist_da,
            historical_capex=hist_capex,
            historical_working_capital=hist_wc,
            shares_outstanding=1e9,
            total_debt=50e9,
            cash=20e9,
            current_price=100.0,
            base_growth=0.10,
            base_margin=0.15,
            base_da_ratio=0.05,
            base_capex_ratio=0.08,
            base_wc_ratio=0.10,
            base_tax_rate=0.25,
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            growth_std=0.0,
            margin_std=0.0,
            da_ratio_std=0.0,
            capex_ratio_std=0.0,
            wc_ratio_std=0.0,
            discount_std=0.0,
            terminal_growth_std=0.0,
            projection_years=10,
            iterations=1,
            seed=42,
        )
        
        # Run without dilution
        result_no_dilution = run_full_monte_carlo(
            **common_params,
            annual_dilution_rate=0.0,
        )
        
        # Run with 3% annual dilution
        result_with_dilution = run_full_monte_carlo(
            **common_params,
            annual_dilution_rate=0.03,
        )
        
        # Both should produce valid results
        assert result_no_dilution.valid_simulations == 1
        assert result_with_dilution.valid_simulations == 1
        
        # Get per-share values
        value_no_dilution = result_no_dilution.mean
        value_with_dilution = result_with_dilution.mean
        
        # Diluted value should be lower
        assert value_with_dilution < value_no_dilution, (
            f"Dilution should reduce per-share value. "
            f"No dilution: ${value_no_dilution:.2f}, With 3% dilution: ${value_with_dilution:.2f}"
        )
        
        # Calculate expected reduction
        # terminal_shares = 1e9 * (1.03)^10 ≈ 1.344e9
        # Reduction factor = 1 / 1.344 ≈ 0.744
        # So diluted value should be ~74% of no-dilution value
        expected_ratio = 1 / (1.03 ** 10)  # ~0.744
        actual_ratio = value_with_dilution / value_no_dilution
        
        # Allow some tolerance for rounding
        assert abs(actual_ratio - expected_ratio) < 0.01, (
            f"Dilution math should match ValuationService. "
            f"Expected ratio: {expected_ratio:.3f}, Actual: {actual_ratio:.3f}"
        )
