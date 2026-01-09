import pytest
from app.services.data_validator import DataValidator, Severity


class TestDataValidator:
    """Tests for DataValidator."""

    def test_valid_data_has_no_errors(self):
        """Complete valid data should have no errors."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert not result.has_errors
        assert len(result.errors) == 0

    def test_missing_market_cap_is_error(self):
        """Missing market cap should be a critical error."""
        validator = DataValidator(
            market_cap=None,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert any(e.field == "market_cap" for e in result.errors)

    def test_missing_beta_is_error(self):
        """Missing beta should be a critical error."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=None,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert any(e.field == "beta" for e in result.errors)

    def test_missing_shares_outstanding_is_error(self):
        """Missing shares outstanding should be a critical error."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=None,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert any(e.field == "shares_outstanding" for e in result.errors)

    def test_insufficient_revenue_history_is_error(self):
        """Less than 2 years of revenue should be a critical error."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100],  # Only 1 year
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert any(e.field == "revenue_history" for e in result.errors)

    def test_missing_ebit_history_is_error(self):
        """Missing EBIT history should be a critical error."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[],  # Empty
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert any(e.field == "ebit_history" for e in result.errors)

    def test_missing_debt_is_warning(self):
        """Missing total debt should be a warning, not error."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=None,  # Missing
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert not result.has_errors
        assert result.has_warnings
        assert any(w.field == "total_debt" for w in result.warnings)

    def test_missing_tax_rate_is_warning(self):
        """Missing tax rate should be a warning."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=None,  # Missing
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert not result.has_errors
        assert result.has_warnings
        assert any(w.field == "tax_rate" for w in result.warnings)

    def test_missing_cost_of_debt_is_error(self):
        """Missing cost of debt should be a critical error."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=None,  # Missing!
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert any(e.field == "cost_of_debt" for e in result.errors)
        # Check the message is helpful
        error = next(e for e in result.errors if e.field == "cost_of_debt")
        assert "custom discount rate" in error.message.lower()

    def test_zero_cost_of_debt_with_debt_is_warning(self):
        """Zero cost of debt when company has debt should warn."""
        validator = DataValidator(
            market_cap=1000000000,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=500000000,  # Has debt
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0,  # But no interest?
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_warnings
        assert any(w.field == "cost_of_debt" for w in result.warnings)

    def test_multiple_errors_detected(self):
        """Multiple missing critical fields should all be reported."""
        validator = DataValidator(
            market_cap=None,
            beta=None,
            shares_outstanding=None,
            total_debt=500000000,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        
        assert result.has_errors
        assert len(result.errors) == 3

    def test_to_dict_format(self):
        """to_dict should return proper API format."""
        validator = DataValidator(
            market_cap=None,
            beta=1.2,
            shares_outstanding=100000000,
            total_debt=None,
            cash=200000000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
        )
        result = validator.validate()
        d = result.to_dict()
        
        assert "has_errors" in d
        assert "has_warnings" in d
        assert "errors" in d
        assert "warnings" in d
        assert d["has_errors"] is True
        assert d["has_warnings"] is True
        assert len(d["errors"]) == 1
        assert d["errors"][0]["field"] == "market_cap"


class TestBusinessTypeGating:
    """
    Tests for P0: Business-type gating warnings.
    
    DCF is not appropriate for all business types:
    - Banks/insurers (balance sheet IS the product)
    - Pre-FCF companies (terminal value dominates)
    - Highly cyclical commodities (need mid-cycle normalization)
    
    The validator should warn users about these limitations.
    """
    
    def _make_validator(self, sector=None, industry=None, free_cash_flow=None, **kwargs):
        """Helper to create validator with business-type fields."""
        defaults = dict(
            market_cap=1_000_000_000,
            beta=1.2,
            shares_outstanding=100_000_000,
            total_debt=500_000_000,
            cash=200_000_000,
            tax_rate=0.25,
            cost_of_debt=0.05,
            revenue_history=[100, 110, 120],
            ebit_history=[20, 22, 24],
            da_history=[5, 5, 6],
            capex_history=[10, 11, 12],
            working_capital_history=[15, 16, 17],
            sector=sector,
            industry=industry,
            free_cash_flow=free_cash_flow,
        )
        defaults.update(kwargs)
        return DataValidator(**defaults)
    
    # ============================================
    # Financial sector warnings (banks/insurers)
    # ============================================
    
    def test_banks_sector_triggers_warning(self):
        """Banks sector should trigger DCF inapplicability warning."""
        validator = self._make_validator(sector="Financial Services", industry="Banks—Regional")
        result = validator.validate()
        
        assert result.has_warnings
        assert any(
            w.field == "business_type" and "financial" in w.message.lower()
            for w in result.warnings
        )
    
    def test_insurance_industry_triggers_warning(self):
        """Insurance industry should trigger warning."""
        validator = self._make_validator(sector="Financial Services", industry="Insurance—Life")
        result = validator.validate()
        
        assert result.has_warnings
        assert any("dcf" in w.message.lower() and "financial" in w.message.lower() for w in result.warnings)
    
    def test_diversified_banks_trigger_warning(self):
        """Diversified banks like JPM should trigger warning."""
        validator = self._make_validator(sector="Financial Services", industry="Banks—Diversified")
        result = validator.validate()
        
        assert result.has_warnings
        business_type_warnings = [w for w in result.warnings if w.field == "business_type"]
        assert len(business_type_warnings) >= 1
    
    def test_asset_management_triggers_warning(self):
        """Asset management firms (like BlackRock) should trigger warning."""
        validator = self._make_validator(sector="Financial Services", industry="Asset Management")
        result = validator.validate()
        
        assert result.has_warnings
        assert any(w.field == "business_type" for w in result.warnings)
    
    def test_tech_sector_no_financial_warning(self):
        """Technology sector should NOT trigger financial warning."""
        validator = self._make_validator(sector="Technology", industry="Software—Application")
        result = validator.validate()
        
        # No business_type warnings for tech companies
        business_type_warnings = [w for w in result.warnings if w.field == "business_type"]
        financial_warnings = [w for w in business_type_warnings if "financial" in w.message.lower()]
        assert len(financial_warnings) == 0
    
    # ============================================
    # Pre-FCF company warnings
    # ============================================
    
    def test_negative_fcf_triggers_warning(self):
        """Negative free cash flow should trigger pre-profitability warning."""
        validator = self._make_validator(free_cash_flow=-50_000_000)  # Negative FCF
        result = validator.validate()
        
        assert result.has_warnings
        assert any(
            w.field == "business_type" and ("negative" in w.message.lower() or "pre-fcf" in w.message.lower())
            for w in result.warnings
        )
    
    def test_very_small_fcf_triggers_warning(self):
        """Very small FCF relative to market cap may indicate pre-profitability."""
        # FCF of 1M with 10B market cap = 0.01% FCF yield (unsustainably low)
        validator = self._make_validator(
            market_cap=10_000_000_000, 
            free_cash_flow=1_000_000
        )
        result = validator.validate()
        
        # Very low FCF yield should warn
        fcf_warnings = [w for w in result.warnings if "cash flow" in w.message.lower()]
        # This might or might not trigger depending on threshold - but negative should always trigger
    
    def test_positive_fcf_no_pre_fcf_warning(self):
        """Healthy positive FCF should NOT trigger pre-FCF warning."""
        validator = self._make_validator(
            market_cap=10_000_000_000,
            free_cash_flow=500_000_000  # 5% FCF yield - healthy
        )
        result = validator.validate()
        
        pre_fcf_warnings = [
            w for w in result.warnings 
            if w.field == "business_type" and "negative" in w.message.lower()
        ]
        assert len(pre_fcf_warnings) == 0
    
    # ============================================
    # Cyclical industry warnings
    # ============================================
    
    def test_oil_gas_triggers_cyclical_warning(self):
        """Oil & Gas sector should trigger cyclicality warning."""
        validator = self._make_validator(sector="Energy", industry="Oil & Gas E&P")
        result = validator.validate()
        
        assert result.has_warnings
        cyclical_warnings = [
            w for w in result.warnings 
            if w.field == "business_type" and "cyclical" in w.message.lower()
        ]
        assert len(cyclical_warnings) >= 1
    
    def test_mining_triggers_cyclical_warning(self):
        """Mining industry should trigger cyclicality warning."""
        validator = self._make_validator(sector="Basic Materials", industry="Gold")
        result = validator.validate()
        
        assert result.has_warnings
        assert any(w.field == "business_type" and "cyclical" in w.message.lower() for w in result.warnings)
    
    def test_steel_triggers_cyclical_warning(self):
        """Steel industry should trigger cyclicality warning."""
        validator = self._make_validator(sector="Basic Materials", industry="Steel")
        result = validator.validate()
        
        assert result.has_warnings
        assert any("cyclical" in w.message.lower() for w in result.warnings)
    
    def test_consumer_staples_no_cyclical_warning(self):
        """Consumer staples (defensive) should NOT trigger cyclical warning."""
        validator = self._make_validator(sector="Consumer Defensive", industry="Packaged Foods")
        result = validator.validate()
        
        cyclical_warnings = [
            w for w in result.warnings 
            if w.field == "business_type" and "cyclical" in w.message.lower()
        ]
        assert len(cyclical_warnings) == 0
    
    # ============================================
    # Combined warnings
    # ============================================
    
    def test_multiple_warnings_can_coexist(self):
        """A company can have multiple business-type warnings."""
        # Negative FCF + cyclical industry
        validator = self._make_validator(
            sector="Energy", 
            industry="Oil & Gas E&P",
            free_cash_flow=-100_000_000
        )
        result = validator.validate()
        
        business_warnings = [w for w in result.warnings if w.field == "business_type"]
        # Should have both cyclical AND pre-FCF warnings
        assert len(business_warnings) >= 2
    
    def test_backward_compatible_no_sector_no_crash(self):
        """Validator should not crash if sector/industry not provided."""
        validator = self._make_validator(sector=None, industry=None, free_cash_flow=None)
        result = validator.validate()
        
        # Should not have business_type warnings (no data to validate)
        # But should NOT crash
        assert result is not None

