"""
Tests for Assumption Audit Trail.

TDD: These tests are written BEFORE the implementation.
"""
import pytest
from datetime import datetime, timedelta
import tempfile
import os

from app.models.assumption_audit import (
    AssumptionField,
    AssumptionChange,
    AuditEntry,
    AssumptionSnapshot,
)
from app.services.audit_repository import AuditRepository


class TestAssumptionSnapshot:
    """Test the AssumptionSnapshot diff logic."""
    
    def test_diff_detects_single_change(self):
        """Should detect when one field changes."""
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            revenue_growth=0.05,
            operating_margin=0.20,
        )
        
        new_values = {
            "revenue_growth": 0.08,
            "operating_margin": 0.20,
        }
        
        changes = snapshot.diff(new_values)
        
        assert len(changes) == 1
        assert changes[0].field == AssumptionField.REVENUE_GROWTH
        assert changes[0].old_value == 0.05
        assert changes[0].new_value == 0.08
    
    def test_diff_detects_multiple_changes(self):
        """Should detect when multiple fields change."""
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            revenue_growth=0.05,
            operating_margin=0.20,
            terminal_growth=0.02,
        )
        
        new_values = {
            "revenue_growth": 0.08,
            "operating_margin": 0.25,
            "terminal_growth": 0.02,  # No change
        }
        
        changes = snapshot.diff(new_values)
        
        assert len(changes) == 2
        fields_changed = {c.field for c in changes}
        assert AssumptionField.REVENUE_GROWTH in fields_changed
        assert AssumptionField.OPERATING_MARGIN in fields_changed
    
    def test_diff_returns_empty_when_no_changes(self):
        """Should return empty list when values are the same."""
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            revenue_growth=0.05,
            operating_margin=0.20,
        )
        
        new_values = {
            "revenue_growth": 0.05,
            "operating_margin": 0.20,
        }
        
        changes = snapshot.diff(new_values)
        
        assert len(changes) == 0
    
    def test_diff_handles_none_to_value(self):
        """Should detect change from None to a value (initial set)."""
        snapshot = AssumptionSnapshot(symbol="AAPL")
        
        new_values = {
            "revenue_growth": 0.05,
        }
        
        changes = snapshot.diff(new_values)
        
        assert len(changes) == 1
        assert changes[0].old_value is None
        assert changes[0].new_value == 0.05
    
    def test_diff_ignores_tiny_float_differences(self):
        """Should not flag changes smaller than 0.0001."""
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            revenue_growth=0.05000001,
        )
        
        new_values = {
            "revenue_growth": 0.05000002,
        }
        
        changes = snapshot.diff(new_values)
        
        assert len(changes) == 0
    
    def test_apply_changes_creates_new_snapshot(self):
        """Should create new snapshot with changes applied."""
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            revenue_growth=0.05,
            operating_margin=0.20,
        )
        
        changes = [
            AssumptionChange(
                field=AssumptionField.REVENUE_GROWTH,
                old_value=0.05,
                new_value=0.08,
            )
        ]
        
        new_snapshot = snapshot.apply_changes(changes)
        
        assert new_snapshot.revenue_growth == 0.08
        assert new_snapshot.operating_margin == 0.20  # Unchanged
        assert snapshot.revenue_growth == 0.05  # Original unchanged


class TestAuditEntry:
    """Test AuditEntry serialization."""
    
    def test_to_dict_serializes_correctly(self):
        """Should serialize to dict for API responses."""
        entry = AuditEntry(
            id=1,
            symbol="AAPL",
            timestamp=datetime(2025, 1, 7, 16, 30, 0),
            changes=[
                AssumptionChange(
                    field=AssumptionField.REVENUE_GROWTH,
                    old_value=0.05,
                    new_value=0.08,
                )
            ],
            note="Updated after Q4 earnings",
            is_initial=False,
        )
        
        result = entry.to_dict()
        
        assert result["id"] == 1
        assert result["symbol"] == "AAPL"
        assert result["timestamp"] == "2025-01-07T16:30:00"
        assert len(result["changes"]) == 1
        assert result["changes"][0]["field"] == "revenue_growth"
        assert result["note"] == "Updated after Q4 earnings"
        assert result["is_initial"] is False


class TestAuditRepository:
    """Test SQLite audit repository."""
    
    @pytest.fixture
    def repo(self):
        """Create a temporary repository for testing."""
        # Use temp file for test database
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        repo = AuditRepository(db_path=path)
        yield repo
        # Cleanup
        os.unlink(path)
    
    def test_save_initial_entry(self, repo):
        """Should save initial analysis entry."""
        entry = AuditEntry(
            id=None,
            symbol="AAPL",
            timestamp=datetime.now(),
            changes=[
                AssumptionChange(
                    field=AssumptionField.REVENUE_GROWTH,
                    old_value=None,
                    new_value=0.05,
                ),
                AssumptionChange(
                    field=AssumptionField.OPERATING_MARGIN,
                    old_value=None,
                    new_value=0.20,
                ),
            ],
            note="Initial analysis",
            is_initial=True,
        )
        
        saved = repo.save_entry(entry)
        
        assert saved.id is not None
        assert saved.id > 0
    
    def test_get_history_for_symbol(self, repo):
        """Should retrieve all entries for a symbol in reverse chronological order."""
        # Save two entries
        entry1 = AuditEntry(
            id=None,
            symbol="AAPL",
            timestamp=datetime.now() - timedelta(hours=2),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05)
            ],
            note="First",
            is_initial=True,
        )
        entry2 = AuditEntry(
            id=None,
            symbol="AAPL",
            timestamp=datetime.now(),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, 0.05, 0.08)
            ],
            note="Second",
            is_initial=False,
        )
        
        repo.save_entry(entry1)
        repo.save_entry(entry2)
        
        history = repo.get_history("AAPL")
        
        assert len(history) == 2
        assert history[0].note == "Second"  # Most recent first
        assert history[1].note == "First"
    
    def test_get_history_filters_by_symbol(self, repo):
        """Should only return entries for the requested symbol."""
        repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05)],
            note=None, is_initial=True,
        ))
        repo.save_entry(AuditEntry(
            id=None, symbol="MSFT", timestamp=datetime.now(),
            changes=[AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.10)],
            note=None, is_initial=True,
        ))
        
        aapl_history = repo.get_history("AAPL")
        msft_history = repo.get_history("MSFT")
        
        assert len(aapl_history) == 1
        assert len(msft_history) == 1
        assert aapl_history[0].symbol == "AAPL"
    
    def test_get_latest_snapshot(self, repo):
        """Should reconstruct current state from history."""
        # Initial
        repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now() - timedelta(hours=2),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05),
                AssumptionChange(AssumptionField.OPERATING_MARGIN, None, 0.20),
            ],
            note="Initial", is_initial=True,
        ))
        # Update
        repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, 0.05, 0.08),
            ],
            note="Updated growth", is_initial=False,
        ))
        
        snapshot = repo.get_latest_snapshot("AAPL")
        
        assert snapshot is not None
        assert snapshot.revenue_growth == 0.08  # Updated
        assert snapshot.operating_margin == 0.20  # From initial
    
    def test_get_latest_snapshot_returns_none_for_unknown_symbol(self, repo):
        """Should return None if no history exists."""
        snapshot = repo.get_latest_snapshot("UNKNOWN")
        
        assert snapshot is None
    
    def test_get_field_history(self, repo):
        """Should get history for a specific field across all entries."""
        repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now() - timedelta(hours=2),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05),
                AssumptionChange(AssumptionField.OPERATING_MARGIN, None, 0.20),
            ],
            note="Initial", is_initial=True,
        ))
        repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, 0.05, 0.08),
            ],
            note="Updated", is_initial=False,
        ))
        
        field_history = repo.get_field_history("AAPL", AssumptionField.REVENUE_GROWTH)
        
        assert len(field_history) == 2
        # Most recent first
        assert field_history[0].new_value == 0.08
        assert field_history[1].new_value == 0.05
    
    def test_has_history(self, repo):
        """Should check if symbol has any audit history."""
        assert repo.has_history("AAPL") is False
        
        repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05)],
            note=None, is_initial=True,
        ))
        
        assert repo.has_history("AAPL") is True
        assert repo.has_history("MSFT") is False

