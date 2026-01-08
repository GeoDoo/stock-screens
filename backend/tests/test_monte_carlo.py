import pytest
from app.services.monte_carlo import (
    MonteCarloSimulator,
    MonteCarloInput,
    MonteCarloResult,
    run_monte_carlo_valuation,
)


class TestMonteCarloInput:
    """Tests for Monte Carlo input configuration."""
    
    def test_create_input_with_base_and_std(self):
        """Can create input with base value and standard deviation."""
        input_config = MonteCarloInput(
            name="growth_rate",
            base_value=0.10,
            std_dev=0.03,
        )
        
        assert input_config.name == "growth_rate"
        assert input_config.base_value == 0.10
        assert input_config.std_dev == 0.03
    
    def test_create_input_with_range(self):
        """Can create input with min/max range."""
        input_config = MonteCarloInput(
            name="margin",
            base_value=0.20,
            min_value=0.15,
            max_value=0.30,
        )
        
        assert input_config.min_value == 0.15
        assert input_config.max_value == 0.30
    
    def test_sample_from_normal(self):
        """Sample from normal distribution when std_dev provided."""
        input_config = MonteCarloInput(
            name="growth",
            base_value=0.10,
            std_dev=0.02,
        )
        
        # Sample many times
        samples = [input_config.sample() for _ in range(1000)]
        
        # Mean should be close to base_value
        mean = sum(samples) / len(samples)
        assert abs(mean - 0.10) < 0.02
    
    def test_sample_from_uniform(self):
        """Sample from uniform distribution when min/max provided."""
        input_config = MonteCarloInput(
            name="margin",
            base_value=0.20,
            min_value=0.10,
            max_value=0.30,
        )
        
        # Sample many times
        samples = [input_config.sample() for _ in range(1000)]
        
        # All samples should be within range
        assert all(0.10 <= s <= 0.30 for s in samples)
        # Mean should be close to center
        mean = sum(samples) / len(samples)
        assert abs(mean - 0.20) < 0.03


class TestMonteCarloSimulator:
    """Tests for the Monte Carlo simulator."""
    
    @pytest.fixture
    def simple_simulator(self):
        """Simple simulator with one input."""
        return MonteCarloSimulator(
            inputs=[
                MonteCarloInput("growth", base_value=0.10, std_dev=0.02),
            ],
            iterations=100,
        )
    
    def test_run_returns_result(self, simple_simulator):
        """Running simulation returns MonteCarloResult."""
        # Simple valuation function
        def value_fn(params):
            return 100 * (1 + params["growth"])
        
        result = simple_simulator.run(value_fn)
        
        assert isinstance(result, MonteCarloResult)
        assert result.iterations == 100
    
    def test_result_has_percentiles(self, simple_simulator):
        """Result includes percentile distribution."""
        def value_fn(params):
            return 100 * (1 + params["growth"])
        
        result = simple_simulator.run(value_fn)
        
        assert "p10" in result.percentiles
        assert "p25" in result.percentiles
        assert "p50" in result.percentiles
        assert "p75" in result.percentiles
        assert "p90" in result.percentiles
        
        # Percentiles should be ordered
        assert result.percentiles["p10"] <= result.percentiles["p25"]
        assert result.percentiles["p25"] <= result.percentiles["p50"]
        assert result.percentiles["p50"] <= result.percentiles["p75"]
        assert result.percentiles["p75"] <= result.percentiles["p90"]
    
    def test_result_has_mean_and_std(self, simple_simulator):
        """Result includes mean and standard deviation."""
        def value_fn(params):
            return 100 * (1 + params["growth"])
        
        result = simple_simulator.run(value_fn)
        
        assert result.mean is not None
        assert result.std_dev is not None
        assert result.std_dev >= 0
    
    def test_multiple_inputs(self):
        """Simulator handles multiple varying inputs."""
        simulator = MonteCarloSimulator(
            inputs=[
                MonteCarloInput("growth", base_value=0.10, std_dev=0.02),
                MonteCarloInput("margin", base_value=0.20, min_value=0.15, max_value=0.25),
            ],
            iterations=100,
        )
        
        def value_fn(params):
            revenue = 100 * (1 + params["growth"])
            profit = revenue * params["margin"]
            return profit * 10  # Simple P/E multiple
        
        result = simulator.run(value_fn)
        
        assert result.iterations == 100
        # With varying margin, we should see more variance
        assert result.std_dev > 0
    
    def test_result_has_simulation_count(self, simple_simulator):
        """Result tracks number of successful simulations."""
        def value_fn(params):
            return 100
        
        result = simple_simulator.run(value_fn)
        
        assert result.valid_simulations == 100
    
    def test_handles_failed_valuations(self):
        """Simulator handles some failed valuations gracefully."""
        simulator = MonteCarloSimulator(
            inputs=[
                MonteCarloInput("growth", base_value=0.05, std_dev=0.10),  # Can go negative
            ],
            iterations=100,
        )
        
        def value_fn(params):
            if params["growth"] < 0:
                return None  # Invalid result
            return 100 * (1 + params["growth"])
        
        result = simulator.run(value_fn)
        
        # Should still produce result with valid simulations
        assert result.valid_simulations <= 100
        assert result.mean is not None
    
    def test_reproducible_with_seed(self):
        """Results are reproducible with same seed."""
        simulator1 = MonteCarloSimulator(
            inputs=[MonteCarloInput("growth", base_value=0.10, std_dev=0.02)],
            iterations=50,
            seed=42,
        )
        simulator2 = MonteCarloSimulator(
            inputs=[MonteCarloInput("growth", base_value=0.10, std_dev=0.02)],
            iterations=50,
            seed=42,
        )
        
        def value_fn(params):
            return 100 * (1 + params["growth"])
        
        result1 = simulator1.run(value_fn)
        result2 = simulator2.run(value_fn)
        
        assert result1.mean == result2.mean


class TestRunMonteCarloValuation:
    """Tests for the high-level Monte Carlo valuation function."""
    
    def test_basic_valuation(self):
        """Run Monte Carlo on basic DCF-like valuation."""
        result = run_monte_carlo_valuation(
            base_revenue=1000,
            base_growth=0.10,
            growth_std=0.03,
            base_margin=0.20,
            margin_std=0.02,
            base_discount_rate=0.10,
            discount_std=0.01,
            terminal_growth=0.03,
            projection_years=5,
            iterations=100,
        )
        
        assert result.mean > 0
        assert result.std_dev > 0
        assert result.percentiles["p50"] > 0
    
    def test_higher_uncertainty_increases_spread(self):
        """More input uncertainty = wider value distribution."""
        # Low uncertainty
        result_low = run_monte_carlo_valuation(
            base_revenue=1000,
            base_growth=0.10,
            growth_std=0.01,
            base_margin=0.20,
            margin_std=0.01,
            base_discount_rate=0.10,
            discount_std=0.005,
            terminal_growth=0.03,
            projection_years=5,
            iterations=200,
        )
        
        # High uncertainty
        result_high = run_monte_carlo_valuation(
            base_revenue=1000,
            base_growth=0.10,
            growth_std=0.05,
            base_margin=0.20,
            margin_std=0.04,
            base_discount_rate=0.10,
            discount_std=0.02,
            terminal_growth=0.03,
            projection_years=5,
            iterations=200,
        )
        
        # High uncertainty should have wider spread
        low_spread = result_low.percentiles["p90"] - result_low.percentiles["p10"]
        high_spread = result_high.percentiles["p90"] - result_high.percentiles["p10"]
        
        assert high_spread > low_spread
