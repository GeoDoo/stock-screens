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
    
    @pytest.mark.asyncio
    async def test_save_initial_entry(self, repo):
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
        
        saved = await repo.save_entry(entry)
        
        assert saved.id is not None
        assert saved.id > 0
    
    @pytest.mark.asyncio
    async def test_get_history_for_symbol(self, repo):
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
        
        await repo.save_entry(entry1)
        await repo.save_entry(entry2)
        
        history = await repo.get_history("AAPL")
        
        assert len(history) == 2
        assert history[0].note == "Second"  # Most recent first
        assert history[1].note == "First"
    
    @pytest.mark.asyncio
    async def test_get_history_filters_by_symbol(self, repo):
        """Should only return entries for the requested symbol."""
        await repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05)],
            note=None, is_initial=True,
        ))
        await repo.save_entry(AuditEntry(
            id=None, symbol="MSFT", timestamp=datetime.now(),
            changes=[AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.10)],
            note=None, is_initial=True,
        ))
        
        aapl_history = await repo.get_history("AAPL")
        msft_history = await repo.get_history("MSFT")
        
        assert len(aapl_history) == 1
        assert len(msft_history) == 1
        assert aapl_history[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self, repo):
        """Should reconstruct current state from history."""
        # Initial
        await repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now() - timedelta(hours=2),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05),
                AssumptionChange(AssumptionField.OPERATING_MARGIN, None, 0.20),
            ],
            note="Initial", is_initial=True,
        ))
        # Update
        await repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, 0.05, 0.08),
            ],
            note="Updated growth", is_initial=False,
        ))
        
        snapshot = await repo.get_latest_snapshot("AAPL")
        
        assert snapshot is not None
        assert snapshot.revenue_growth == 0.08  # Updated
        assert snapshot.operating_margin == 0.20  # From initial
    
    @pytest.mark.asyncio
    async def test_get_latest_snapshot_returns_none_for_unknown_symbol(self, repo):
        """Should return None if no history exists."""
        snapshot = await repo.get_latest_snapshot("UNKNOWN")
        
        assert snapshot is None
    
    @pytest.mark.asyncio
    async def test_get_field_history(self, repo):
        """Should get history for a specific field across all entries."""
        await repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now() - timedelta(hours=2),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05),
                AssumptionChange(AssumptionField.OPERATING_MARGIN, None, 0.20),
            ],
            note="Initial", is_initial=True,
        ))
        await repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[
                AssumptionChange(AssumptionField.REVENUE_GROWTH, 0.05, 0.08),
            ],
            note="Updated", is_initial=False,
        ))
        
        field_history = await repo.get_field_history("AAPL", AssumptionField.REVENUE_GROWTH)
        
        assert len(field_history) == 2
        # Most recent first
        assert field_history[0].new_value == 0.08
        assert field_history[1].new_value == 0.05
    
    @pytest.mark.asyncio
    async def test_has_history(self, repo):
        """Should check if symbol has any audit history."""
        assert await repo.has_history("AAPL") is False
        
        await repo.save_entry(AuditEntry(
            id=None, symbol="AAPL", timestamp=datetime.now(),
            changes=[AssumptionChange(AssumptionField.REVENUE_GROWTH, None, 0.05)],
            note=None, is_initial=True,
        ))
        
        assert await repo.has_history("AAPL") is True
        assert await repo.has_history("MSFT") is False



class TestNullNewValue:
    """
    Regression tests for new_value being None.
    
    Bug: AssumptionChange.new_value was typed as float (not Optional[float]),
    but the diff() method can produce None values when clearing an assumption.
    This caused:
    1. Type annotation mismatch
    2. DB insert failure (NOT NULL constraint)
    3. apply_changes crash when doing int(None)
    """
    
    @pytest.fixture
    def repo(self):
        """Create a temporary repository for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        repo = AuditRepository(db_path=path)
        yield repo
        os.unlink(path)
    
    def test_diff_handles_value_to_none(self):
        """
        Should detect change from a value to None (clearing an assumption).
        
        Use case: User had custom discount rate, now wants to use default WACC.
        """
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            discount_rate=0.10,
        )
        
        new_values = {
            "discount_rate": None,  # Clear the custom discount rate
        }
        
        changes = snapshot.diff(new_values)
        
        assert len(changes) == 1
        assert changes[0].field == AssumptionField.DISCOUNT_RATE
        assert changes[0].old_value == 0.10
        assert changes[0].new_value is None
    
    def test_apply_changes_handles_none_new_value(self):
        """
        apply_changes should handle new_value=None without crashing.
        """
        snapshot = AssumptionSnapshot(
            symbol="AAPL",
            discount_rate=0.10,
            projection_years=10,
        )
        
        changes = [
            AssumptionChange(
                field=AssumptionField.DISCOUNT_RATE,
                old_value=0.10,
                new_value=None,
            ),
            AssumptionChange(
                field=AssumptionField.PROJECTION_YEARS,
                old_value=10,
                new_value=None,
            ),
        ]
        
        # Should not crash
        new_snapshot = snapshot.apply_changes(changes)
        
        assert new_snapshot.discount_rate is None
        assert new_snapshot.projection_years is None
    
    @pytest.mark.asyncio
    async def test_repo_saves_none_new_value(self, repo):
        """
        Repository should be able to save entries where new_value is None.
        """
        entry = AuditEntry(
            id=None,
            symbol="AAPL",
            timestamp=datetime.now(),
            changes=[
                AssumptionChange(
                    field=AssumptionField.DISCOUNT_RATE,
                    old_value=0.10,
                    new_value=None,  # Clearing the value
                )
            ],
            note="Cleared custom discount rate",
            is_initial=False,
        )
        
        # Should not raise
        saved = await repo.save_entry(entry)
        
        assert saved.id is not None
        
        # Verify retrieval
        history = await repo.get_history("AAPL")
        assert len(history) == 1
        assert history[0].changes[0].new_value is None
    
    def test_to_dict_serializes_none_new_value(self):
        """
        AuditEntry.to_dict() should correctly serialize None new_value.
        """
        entry = AuditEntry(
            id=1,
            symbol="AAPL",
            timestamp=datetime(2025, 1, 9, 10, 0, 0),
            changes=[
                AssumptionChange(
                    field=AssumptionField.DISCOUNT_RATE,
                    old_value=0.10,
                    new_value=None,
                )
            ],
            note="Test",
            is_initial=False,
        )
        
        result = entry.to_dict()
        
        assert result["changes"][0]["new_value"] is None


class TestSchemaMigration:
    """
    Regression tests for schema migrations on existing databases.
    
    Bug: The audit_changes table was created with new_value NOT NULL,
    but we now allow NULL (for clearing assumptions). Existing databases
    retain the old constraint and fail on NULL inserts.
    """
    
    @pytest.mark.asyncio
    async def test_migration_allows_null_new_value_on_old_schema(self):
        """
        Databases created with old schema should be migrated to allow NULL.
        
        This simulates an existing database with the NOT NULL constraint.
        """
        import sqlite3
        
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        try:
            # Create "old" schema with NOT NULL constraint
            conn = sqlite3.connect(path)
            conn.executescript("""
                CREATE TABLE audit_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    note TEXT,
                    is_initial INTEGER NOT NULL DEFAULT 0
                );
                
                CREATE TABLE audit_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    field TEXT NOT NULL,
                    old_value REAL,
                    new_value REAL NOT NULL,  -- OLD: NOT NULL constraint
                    FOREIGN KEY (entry_id) REFERENCES audit_entries(id)
                );
            """)
            conn.commit()
            conn.close()
            
            # Now open with AuditRepository (should migrate)
            repo = AuditRepository(db_path=path)
            
            # Try to insert an entry with new_value=None
            entry = AuditEntry(
                id=None,
                symbol="AAPL",
                timestamp=datetime.now(),
                changes=[
                    AssumptionChange(
                        field=AssumptionField.DISCOUNT_RATE,
                        old_value=0.10,
                        new_value=None,  # This should work after migration
                    )
                ],
                note="Clear discount rate",
                is_initial=False,
            )
            
            # Should NOT raise IntegrityError
            saved = await repo.save_entry(entry)
            assert saved.id is not None
            
            # Verify it was saved correctly
            history = await repo.get_history("AAPL")
            assert len(history) == 1
            assert history[0].changes[0].new_value is None
            
        finally:
            os.unlink(path)
