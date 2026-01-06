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


