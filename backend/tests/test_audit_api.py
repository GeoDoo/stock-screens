"""
Tests for Audit Trail API endpoints.

TDD: Written BEFORE endpoint implementation.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import tempfile
import os

from app.main import app
from app.services.audit_repository import AuditRepository, get_audit_repository


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    repo = AuditRepository(db_path=path)
    yield repo, path
    os.unlink(path)


@pytest.fixture
def client(temp_repo):
    """Create test client with temporary database."""
    repo, path = temp_repo
    
    # Override the dependency
    def override_get_repo():
        return repo
    
    app.dependency_overrides[get_audit_repository] = override_get_repo
    
    client = TestClient(app)
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


class TestAuditTrailAPI:
    """Test audit trail REST endpoints."""
    
    def test_record_initial_analysis(self, client):
        """POST /api/audit/{symbol} should record initial analysis."""
        response = client.post("/api/audit/AAPL", json={
            "assumptions": {
                "revenue_growth": 0.05,
                "operating_margin": 0.25,
                "terminal_growth": 0.02,
                "discount_rate": 0.10,
                "projection_years": 5,
                "market_risk_premium": 0.05,
            },
            "note": "Initial analysis based on TTM hints",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["symbol"] == "AAPL"
        assert data["is_initial"] is True
        assert len(data["changes"]) == 6
    
    def test_record_assumption_update(self, client):
        """POST should detect changes from previous snapshot."""
        # First, create initial
        client.post("/api/audit/AAPL", json={
            "assumptions": {
                "revenue_growth": 0.05,
                "operating_margin": 0.25,
            },
            "note": "Initial",
        })
        
        # Then update
        response = client.post("/api/audit/AAPL", json={
            "assumptions": {
                "revenue_growth": 0.08,  # Changed
                "operating_margin": 0.25,  # Same
            },
            "note": "Updated after earnings call",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["is_initial"] is False
        assert len(data["changes"]) == 1
        assert data["changes"][0]["field"] == "revenue_growth"
        assert data["changes"][0]["old_value"] == 0.05
        assert data["changes"][0]["new_value"] == 0.08
    
    def test_record_returns_no_changes_if_nothing_changed(self, client):
        """POST should return 200 with empty changes if nothing changed."""
        # Initial
        client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.05},
            "note": "Initial",
        })
        
        # Same values
        response = client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.05},
            "note": "No change",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No changes detected"
        assert data["changes"] == []
    
    def test_get_history(self, client):
        """GET /api/audit/{symbol}/history should return entries."""
        # Create some entries
        client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.05},
            "note": "First",
        })
        client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.08},
            "note": "Second",
        })
        
        response = client.get("/api/audit/AAPL/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Most recent first
        assert data[0]["note"] == "Second"
        assert data[1]["note"] == "First"
    
    def test_get_history_empty_for_unknown(self, client):
        """GET should return empty list for unknown symbol."""
        response = client.get("/api/audit/UNKNOWN/history")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_current_snapshot(self, client):
        """GET /api/audit/{symbol}/snapshot should return current state."""
        # Create entries
        client.post("/api/audit/AAPL", json={
            "assumptions": {
                "revenue_growth": 0.05,
                "operating_margin": 0.25,
            },
            "note": "Initial",
        })
        client.post("/api/audit/AAPL", json={
            "assumptions": {
                "revenue_growth": 0.08,
                "operating_margin": 0.25,
            },
            "note": "Updated",
        })
        
        response = client.get("/api/audit/AAPL/snapshot")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["revenue_growth"] == 0.08
        assert data["operating_margin"] == 0.25
    
    def test_get_snapshot_returns_404_for_unknown(self, client):
        """GET snapshot should return 404 if no history exists."""
        response = client.get("/api/audit/UNKNOWN/snapshot")
        
        assert response.status_code == 404
    
    def test_get_field_history(self, client):
        """GET /api/audit/{symbol}/field/{field} should return field changes."""
        # Create entries with revenue_growth changes
        client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.05},
            "note": "Initial",
        })
        client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.08},
            "note": "Update 1",
        })
        client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.10},
            "note": "Update 2",
        })
        
        response = client.get("/api/audit/AAPL/field/revenue_growth")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Most recent first
        assert data[0]["new_value"] == 0.10
        assert data[1]["new_value"] == 0.08
        assert data[2]["new_value"] == 0.05
    
    def test_get_field_history_invalid_field(self, client):
        """GET field history should return 400 for invalid field name."""
        response = client.get("/api/audit/AAPL/field/invalid_field")
        
        assert response.status_code == 400
    
    def test_symbol_case_insensitive(self, client):
        """API should treat symbols as case-insensitive."""
        client.post("/api/audit/aapl", json={
            "assumptions": {"revenue_growth": 0.05},
            "note": "Lowercase",
        })
        
        response = client.get("/api/audit/AAPL/history")
        
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_timestamps_are_utc_aware(self, client):
        """
        P0.3 Fix: Audit timestamps must be UTC-aware for forensic integrity.
        
        Naive timestamps (without timezone) create ambiguity in multi-machine
        or later analysis scenarios. All timestamps should be UTC-aware.
        """
        response = client.post("/api/audit/AAPL", json={
            "assumptions": {"revenue_growth": 0.05},
            "note": "Test UTC timestamp",
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Timestamp should be a valid ISO format string with timezone
        timestamp_str = data["timestamp"]
        
        # Parse the timestamp - it should have timezone info
        parsed = datetime.fromisoformat(timestamp_str)
        assert parsed.tzinfo is not None, (
            f"Timestamp '{timestamp_str}' is naive (no timezone). "
            "Audit timestamps must be UTC-aware for forensic integrity."
        )
        
        # Verify it's actually UTC (offset should be 0)
        assert parsed.utcoffset().total_seconds() == 0, (
            f"Timestamp should be in UTC, got offset {parsed.utcoffset()}"
        )