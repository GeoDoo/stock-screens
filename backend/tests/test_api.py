import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement


client = TestClient(app)


def create_mock_stock_data(
    symbol="AAPL",
    name="Apple Inc.",
    industry="Consumer Electronics",
    sector="Technology",
    beta=1.25,
    market_cap=3000000000000,
    shares_outstanding=15744231000,
    price=190.0,
):
    """Create a mock StockData object for testing."""
    return StockData(
        profile=CompanyProfile(
            symbol=symbol,
            name=name,
            price=price,
            market_cap=market_cap,
            beta=beta,
            shares_outstanding=shares_outstanding,
            currency="USD",
            exchange="NASDAQ",
            industry=industry,
            sector=sector,
        ),
        financials=[
            FinancialStatement(
                date="2024-01-01",
                period="annual",
                revenue=383285000000,
                cost_of_revenue=214137000000,
                gross_profit=169148000000,
                operating_income=114301000000,
                net_income=96995000000,
                interest_expense=3933000000,
                income_tax_expense=16741000000,
                total_assets=352583000000,
                total_liabilities=290437000000,
                total_equity=62146000000,
                total_debt=111088000000,
                cash_and_equivalents=29965000000,
                current_assets=143566000000,
                current_liabilities=145308000000,
                operating_cash_flow=110543000000,
                capital_expenditure=-10959000000,
                free_cash_flow=99584000000,
                depreciation_amortization=11519000000,
            ),
            FinancialStatement(
                date="2023-01-01",
                period="annual",
                revenue=365817000000,
                cost_of_revenue=208000000000,
                gross_profit=157817000000,
                operating_income=108949000000,
                net_income=94680000000,
                interest_expense=2645000000,
                income_tax_expense=14527000000,
                total_assets=330000000000,
                total_liabilities=268000000000,
                total_equity=62000000000,
                total_debt=100000000000,
                cash_and_equivalents=25000000000,
                current_assets=140000000000,
                current_liabilities=140000000000,
                operating_cash_flow=100000000000,
                capital_expenditure=-10000000000,
                free_cash_flow=90000000000,
                depreciation_amortization=11000000000,
            ),
        ],
        provider="fmp",
    )


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStockEndpoint:
    def test_get_stock_returns_data_and_hints(self):
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL?provider=fmp")

            assert response.status_code == 200
            result = response.json()
            
            # Check structure
            assert "symbol" in result
            assert "company_name" in result
            assert "industry" in result
            assert "sector" in result
            assert "data" in result
            assert "hints" in result
            assert "validation" in result
            
            # Check data (read-only from provider)
            assert result["symbol"] == "AAPL"
            assert result["company_name"] == "Apple Inc."
            assert result["industry"] == "Consumer Electronics"
            assert result["sector"] == "Technology"
            assert result["data"]["beta"] == 1.25
            assert result["data"]["market_cap"] == 3000000000000
            assert result["data"]["risk_free_rate"] == 0.045
            
            # Check hints (calculated from historical)
            assert "revenue_growth" in result["hints"]
            assert "operating_margin" in result["hints"]
            
            # Check validation
            assert "has_errors" in result["validation"]
            assert "has_warnings" in result["validation"]
            
            # Check provenance (P2 enhancement - data source transparency)
            assert "provenance" in result
            provenance = result["provenance"]
            assert "tax_rate" in provenance
            assert "shares_outstanding" in provenance
            assert "revenue_source" in provenance
            assert "cost_of_debt" in provenance
            
            # Each provenance item has source, description, confidence
            tax_prov = provenance["tax_rate"]
            assert "source" in tax_prov
            assert "description" in tax_prov
            assert "confidence" in tax_prov
            assert tax_prov["confidence"] in ["high", "medium", "low"]

    def test_get_stock_without_api_key(self):
        with patch("app.routers.stock.FMP_API_KEY", ""):
            response = client.get("/api/stock/AAPL?provider=fmp")
            assert response.status_code == 400
            assert "API key" in response.json()["detail"]

    def test_get_stock_handles_missing_industry_sector(self):
        """Industry and sector should be None if not provided by provider."""
        mock_stock_data = create_mock_stock_data(
            symbol="TEST",
            name="Test Corp",
            industry=None,
            sector=None,
            beta=1.0,
            market_cap=1000000000,
        )
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/TEST?provider=fmp")
            
            assert response.status_code == 200
            result = response.json()
            assert result["industry"] is None
            assert result["sector"] is None

    def test_get_stock_unknown_provider(self):
        """Unknown provider should return 400."""
        response = client.get("/api/stock/AAPL?provider=invalid")
        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]


class TestValuationEndpoint:
    @pytest.fixture
    def mock_valuation_result(self):
        return {
            "symbol": "AAPL",
            "intrinsic_value_per_share": 187.45,
            "enterprise_value": 3100000000000,
            "equity_value": 3018877000000,
            "market_cap": 3000000000000,
            "wacc": 0.0923,
            "projections": [],
            "inputs": {},
        }

    def test_run_valuation_requires_all_inputs(self):
        """Valuation should require all user inputs."""
        mock_client = MagicMock()
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            # Missing required fields should fail
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={}
            )
            assert response.status_code == 422  # Validation error

    def test_run_valuation_with_all_inputs(self, mock_valuation_result):
        mock_client = MagicMock()
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.ValuationService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.value_stock = AsyncMock(return_value=mock_valuation_result)

            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.10,
                    "operating_margin": 0.30,
                    "terminal_growth_rate": 0.03,
                    "market_risk_premium": 0.06,
                    "projection_years": 5,
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["intrinsic_value_per_share"] == 187.45

    def test_run_valuation_passes_user_inputs(self, mock_valuation_result):
        mock_client = MagicMock()
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.ValuationService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.value_stock = AsyncMock(return_value=mock_valuation_result)

            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.15,
                    "operating_margin": 0.32,
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.07,
                    "projection_years": 10,
                }
            )

            assert response.status_code == 200
            # Verify user inputs were passed correctly
            mock_instance.value_stock.assert_called_once()
            call_kwargs = mock_instance.value_stock.call_args.kwargs
            assert call_kwargs["revenue_growth"] == 0.15
            assert call_kwargs["operating_margin"] == 0.32
            assert call_kwargs["terminal_growth_rate"] == 0.025
            assert call_kwargs["market_risk_premium"] == 0.07
            assert call_kwargs["projection_years"] == 10


class TestScenarioEndpoint:
    def test_scenarios_with_custom_discount_rate(self):
        """Scenario analysis should accept custom discount rate override."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/scenarios?provider=fmp",
                json={
                    "projection_years": 10,
                    "market_risk_premium": 0.06,
                    "discount_rate_override": 0.10,  # Custom 10% rate
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "scenarios" in data
            assert data["wacc"] == 0.10  # Should use our custom rate

    def test_scenarios_without_wacc_requires_custom_rate(self):
        """Scenario analysis should fail if WACC unavailable and no custom rate."""
        # Create stock data with missing beta (WACC can't be calculated)
        mock_stock_data = create_mock_stock_data(beta=None)
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/scenarios?provider=fmp",
                json={
                    "projection_years": 10,
                    "market_risk_premium": 0.06,
                    # No discount_rate_override provided
                }
            )
            
            assert response.status_code == 400
            assert "Cannot calculate WACC" in response.json()["detail"]

    def test_scenarios_with_missing_beta_and_custom_rate_succeeds(self):
        """Scenario analysis should work with custom rate even if beta missing."""
        # Create stock data with missing beta
        mock_stock_data = create_mock_stock_data(beta=None)
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/scenarios?provider=fmp",
                json={
                    "projection_years": 10,
                    "market_risk_premium": 0.06,
                    "discount_rate_override": 0.12,  # Custom rate bypasses WACC
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["wacc"] == 0.12  # Uses our custom rate


class TestAdvancedDCFOptions:
    """Test mid-year discounting and WC mode API parameters."""
    
    def test_valuation_accepts_mid_year_discounting(self):
        """Valuation endpoint should accept use_mid_year_discounting parameter."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.05,
                    "operating_margin": 0.25,
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.06,
                    "projection_years": 10,
                    "use_mid_year_discounting": True,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "intrinsic_value_per_share" in data
    
    def test_valuation_accepts_wc_mode_level(self):
        """Valuation endpoint should accept wc_mode='level' parameter."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.05,
                    "operating_margin": 0.25,
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.06,
                    "projection_years": 10,
                    "wc_mode": "level",
                }
            )
            
            assert response.status_code == 200
    
    def test_valuation_accepts_wc_mode_incremental(self):
        """Valuation endpoint should accept wc_mode='incremental' parameter."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.05,
                    "operating_margin": 0.25,
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.06,
                    "projection_years": 10,
                    "wc_mode": "incremental",
                }
            )
            
            assert response.status_code == 200
    
    def test_mid_year_discounting_changes_result(self):
        """Mid-year discounting should produce higher intrinsic value."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        base_request = {
            "revenue_growth": 0.05,
            "operating_margin": 0.25,
            "terminal_growth_rate": 0.025,
            "market_risk_premium": 0.06,
            "projection_years": 10,
        }

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            # Without mid-year discounting
            response_without = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={**base_request, "use_mid_year_discounting": False}
            )
            value_without = response_without.json()["intrinsic_value_per_share"]
            
            # With mid-year discounting
            response_with = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={**base_request, "use_mid_year_discounting": True}
            )
            value_with = response_with.json()["intrinsic_value_per_share"]
            
            # Mid-year discounting should give higher value (cash flows arrive sooner)
            assert value_with > value_without
    
    def test_valuation_accepts_multi_stage_growth(self):
        """Valuation endpoint should accept growth_stages for multi-stage DCF."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.05,  # Should be ignored when stages provided
                    "operating_margin": 0.25,
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.06,
                    "projection_years": 10,  # Should be ignored when stages provided
                    "growth_stages": [
                        {"name": "High Growth", "years": 3, "growth_rate": 0.20},
                        {"name": "Fade", "years": 4, "growth_rate": 0.20, "end_growth_rate": 0.08},
                        {"name": "Mature", "years": 3, "growth_rate": 0.05},
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "intrinsic_value_per_share" in data
            # Should have 10 projections (3 + 4 + 3)
            assert len(data["projections"]) == 10
    
    def test_multi_stage_growth_produces_different_result(self):
        """Multi-stage growth should produce different value than constant growth."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        base_request = {
            "operating_margin": 0.25,
            "terminal_growth_rate": 0.025,
            "market_risk_premium": 0.06,
        }

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            # Constant 10% growth for 10 years
            response_constant = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={**base_request, "revenue_growth": 0.10, "projection_years": 10}
            )
            value_constant = response_constant.json()["intrinsic_value_per_share"]
            
            # Multi-stage: 20% → 10% → 5% over same period
            response_stages = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    **base_request,
                    "revenue_growth": 0.10,  # Ignored
                    "projection_years": 10,  # Ignored
                    "growth_stages": [
                        {"name": "High", "years": 3, "growth_rate": 0.20},
                        {"name": "Fade", "years": 4, "growth_rate": 0.20, "end_growth_rate": 0.05},
                        {"name": "Mature", "years": 3, "growth_rate": 0.05},
                    ]
                }
            )
            value_stages = response_stages.json()["intrinsic_value_per_share"]
            
            # Values should be different (multi-stage has higher early growth)
            assert value_constant != value_stages

    def test_multi_stage_economics_margin_fade(self):
        """
        Multi-stage economics should allow margin fade.
        
        This tests the institutional-grade modeling where:
        - High-growth phase: Lower margins (investing in growth)
        - Mature phase: Higher margins (operating leverage)
        """
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            # Multi-stage with margin expansion
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.10,
                    "operating_margin": 0.15,  # Fallback if not in stages
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.06,
                    "projection_years": 10,
                    "growth_stages": [
                        {
                            "name": "High Growth",
                            "years": 3,
                            "growth_rate": 0.25,
                            "operating_margin": 0.15,  # Lower margins during growth
                        },
                        {
                            "name": "Margin Expansion",
                            "years": 4,
                            "growth_rate": 0.25,
                            "end_growth_rate": 0.08,
                            "operating_margin": 0.15,
                            "end_operating_margin": 0.28,  # Margins expand
                        },
                        {
                            "name": "Mature",
                            "years": 3,
                            "growth_rate": 0.05,
                            "operating_margin": 0.28,  # Stable mature margins
                        },
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "intrinsic_value_per_share" in data
            
            # Should have 10 projections with varying margins
            projections = data["projections"]
            assert len(projections) == 10
            
            # Verify margin expansion is reflected in projections
            # Early years should have lower EBIT margins, later years higher
            year_1_margin = projections[0]["ebit"] / projections[0]["revenue"]
            year_10_margin = projections[9]["ebit"] / projections[9]["revenue"]
            
            # Mature margin should be higher than growth margin
            assert year_10_margin > year_1_margin, (
                f"Margin should expand from {year_1_margin:.2%} to {year_10_margin:.2%}"
            )


class TestFullMonteCarloEndpoint:
    """Tests for Full-Model Monte Carlo API endpoint."""
    
    def test_full_monte_carlo_returns_decision_metrics(self):
        """Full MC endpoint should return decision-grade metrics."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/monte-carlo-full?provider=fmp",
                json={
                    "base_growth": 0.08,
                    "base_margin": 0.25,
                    "base_da_ratio": 0.05,
                    "base_capex_ratio": 0.08,
                    "base_wc_ratio": 0.10,
                    "base_tax_rate": 0.25,
                    "base_discount_rate": 0.10,
                    "base_terminal_growth": 0.03,
                    "iterations": 100,  # Small for speed
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have mode indicator
            assert data["mode"] == "full"
            
            # Should have per-share distribution
            assert "per_share" in data
            assert "mean" in data["per_share"]
            assert "median" in data["per_share"]
            assert "percentiles" in data["per_share"]
            
            # Should have decision metrics
            assert "decision_metrics" in data
            metrics = data["decision_metrics"]
            assert "probability_positive_upside" in metrics
            assert "probability_20pct_upside" in metrics
            assert "probability_20pct_downside" in metrics
            assert "cvar_10" in metrics
            assert "margin_of_safety_mean" in metrics
    
    def test_full_monte_carlo_with_correlations(self):
        """Full MC should accept correlation parameters."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/monte-carlo-full?provider=fmp",
                json={
                    "base_growth": 0.08,
                    "base_margin": 0.25,
                    "base_da_ratio": 0.05,
                    "base_capex_ratio": 0.08,
                    "base_wc_ratio": 0.10,
                    "base_discount_rate": 0.10,
                    "iterations": 100,
                    "growth_margin_correlation": -0.3,  # Custom correlation
                    "growth_capex_correlation": 0.4,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should echo back correlations in inputs
            assert data["inputs"]["correlations"]["growth_margin"] == -0.3
            assert data["inputs"]["correlations"]["growth_capex"] == 0.4
    
    def test_full_monte_carlo_valid_simulations_count(self):
        """Full MC should report valid simulation count."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/monte-carlo-full?provider=fmp",
                json={
                    "base_growth": 0.08,
                    "base_margin": 0.25,
                    "base_da_ratio": 0.05,
                    "base_capex_ratio": 0.08,
                    "base_wc_ratio": 0.10,
                    "base_discount_rate": 0.10,
                    "iterations": 100,
                }
            )
            
            data = response.json()
            assert "valid_simulations" in data
            # Most should be valid for reasonable inputs
            assert data["valid_simulations"] >= 50


class TestSensitivityMatrix:
    """Tests for 2D sensitivity matrix endpoint."""
    
    def test_margin_growth_matrix(self):
        """Should generate margin × growth sensitivity matrix."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/sensitivity-matrix?provider=fmp",
                json={
                    "matrix_type": "margin_growth",
                    "base_growth": 0.10,
                    "base_margin": 0.20,
                    "base_discount_rate": 0.10,
                    "terminal_growth": 0.03,
                    "projection_years": 5,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check structure
            assert data["matrix_type"] == "margin_growth"
            assert "margins" in data
            assert "growth_rates" in data
            assert "matrix" in data
            assert "base_values" in data
            
            # Should be 5×5 matrix (default steps)
            assert len(data["margins"]) == 5
            assert len(data["growth_rates"]) == 5
            assert len(data["matrix"]) == 5
            assert len(data["matrix"][0]) == 5
            
            # Center cell should exist and be positive
            center_value = data["matrix"][2][2]  # 0-indexed center of 5×5
            assert center_value is not None
            assert center_value > 0
            
            # Base values should be recorded
            assert data["base_values"]["margin"] == 0.20
            assert data["base_values"]["growth"] == 0.10
    
    def test_wacc_terminal_matrix(self):
        """Should generate WACC × terminal growth sensitivity matrix."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/sensitivity-matrix?provider=fmp",
                json={
                    "matrix_type": "wacc_terminal",
                    "base_growth": 0.10,
                    "base_margin": 0.20,
                    "base_discount_rate": 0.10,
                    "terminal_growth": 0.03,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check structure
            assert data["matrix_type"] == "wacc_terminal"
            assert "discount_rates" in data
            assert "terminal_growth_rates" in data
            assert "matrix" in data
            
            # Should be 5×5 matrix
            assert len(data["discount_rates"]) == 5
            assert len(data["terminal_growth_rates"]) == 5
            assert len(data["matrix"]) == 5
            
            # Higher discount rate should give lower value
            # (Row 0 is lowest WACC, Row 4 is highest)
            center_col = 2
            low_wacc_value = data["matrix"][0][center_col]
            high_wacc_value = data["matrix"][4][center_col]
            if low_wacc_value is not None and high_wacc_value is not None:
                assert low_wacc_value > high_wacc_value
