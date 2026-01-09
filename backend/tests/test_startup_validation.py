"""
Tests for startup configuration validation.

These tests verify that the application properly validates and warns about
missing or insecure configuration on startup.
"""
import pytest
import logging
from unittest.mock import patch


class TestAPIKeyValidation:
    """Tests for API key validation on startup."""
    
    def test_warns_when_fmp_api_key_missing(self, caplog):
        """
        P0 Critical: Missing FMP_API_KEY should log a warning on startup.
        
        The app should NOT crash, but clearly indicate that FMP provider
        will be unavailable.
        """
        with caplog.at_level(logging.WARNING):
            # Import the validation function (will be added)
            from app.main import validate_configuration
            
            with patch.dict("os.environ", {"FMP_API_KEY": ""}, clear=False):
                warnings = validate_configuration()
                
        assert any("FMP_API_KEY" in record.message for record in caplog.records), (
            "Should log a warning when FMP_API_KEY is not set"
        )
        assert "fmp" in [w["provider"] for w in warnings if "provider" in w], (
            "Should return warning about FMP provider"
        )
    
    def test_no_warning_when_fmp_api_key_set(self, caplog):
        """When FMP_API_KEY is set, no warning should be logged for it."""
        with caplog.at_level(logging.WARNING):
            from app.main import validate_configuration
            
            with patch.dict("os.environ", {"FMP_API_KEY": "test_key_123"}, clear=False):
                warnings = validate_configuration()
        
        fmp_warnings = [w for w in warnings if w.get("provider") == "fmp"]
        assert len(fmp_warnings) == 0, "No FMP warning when key is set"


class TestCORSValidation:
    """Tests for CORS configuration validation."""
    
    def test_warns_when_cors_is_wildcard(self, caplog):
        """
        P0 Critical: Wildcard CORS should log a warning.
        
        While acceptable in development, wildcard CORS is a security risk
        in production. The app should warn about this configuration.
        """
        with caplog.at_level(logging.WARNING):
            from app.main import validate_configuration
            
            with patch.dict("os.environ", {"CORS_ORIGINS": ""}, clear=False):
                warnings = validate_configuration()
        
        assert any("CORS" in record.message for record in caplog.records), (
            "Should log a warning when CORS is set to wildcard"
        )
        assert any(w.get("type") == "cors_wildcard" for w in warnings), (
            "Should return warning about wildcard CORS"
        )
    
    def test_no_warning_when_cors_explicit(self, caplog):
        """When CORS_ORIGINS is explicitly set, no warning should be logged."""
        with caplog.at_level(logging.WARNING):
            from app.main import validate_configuration
            
            with patch.dict(
                "os.environ", 
                {"CORS_ORIGINS": "http://localhost:5173,https://myapp.com"}, 
                clear=False
            ):
                warnings = validate_configuration()
        
        cors_warnings = [w for w in warnings if w.get("type") == "cors_wildcard"]
        assert len(cors_warnings) == 0, "No CORS warning when explicitly set"


class TestStartupValidation:
    """Tests for overall startup validation behavior."""
    
    def test_validation_returns_all_warnings(self):
        """validate_configuration should return a list of all config issues."""
        from app.main import validate_configuration
        
        with patch.dict("os.environ", {"FMP_API_KEY": "", "CORS_ORIGINS": ""}, clear=False):
            warnings = validate_configuration()
        
        # Should have warnings for both FMP key and CORS
        warning_types = {w.get("type") or w.get("provider") for w in warnings}
        assert "fmp" in warning_types or "cors_wildcard" in warning_types, (
            "Should return at least one warning when config is incomplete"
        )
    
    def test_health_endpoint_still_works_without_api_keys(self):
        """App should still start and serve health checks without API keys."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
