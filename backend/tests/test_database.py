"""
Tests for shared database module.
TDD: Ensures single database is used across all services.
"""
import pytest
import tempfile
import os
from pathlib import Path


class TestSharedDatabase:
    """Test that all services use the same database."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_database_module_provides_path(self):
        """Database module should provide a single path."""
        from app.services.database import get_db_path
        
        path = get_db_path()
        assert path.endswith('.db')
        assert 'stock_screens' in path
    
    def test_database_module_provides_connection(self, temp_db):
        """Database module should provide connection helper."""
        from app.services.database import get_connection
        
        with get_connection(temp_db) as conn:
            # Should be able to execute queries
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")
            result = conn.execute("SELECT * FROM test").fetchone()
            assert result[0] == 1
    
    def test_connection_is_context_manager(self, temp_db):
        """Connection should auto-close via context manager."""
        from app.services.database import get_connection
        
        with get_connection(temp_db) as conn:
            conn.execute("CREATE TABLE test (id INTEGER)")
        
        # Connection should be closed, but we can open a new one
        with get_connection(temp_db) as conn:
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()
            assert result[0] == 'test'
    
    def test_rate_limiter_uses_shared_db(self, temp_db):
        """Rate limiter should use the shared database path."""
        from app.services.rate_limiter_sqlite import RateLimiterSQLite
        
        limiter = RateLimiterSQLite(db_path=temp_db)
        limiter.record_call("fmp")
        limiter.close()
        
        # Verify table exists in shared db
        from app.services.database import get_connection
        with get_connection(temp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='api_calls'"
            ).fetchone()
            assert tables is not None
    
    def test_audit_repository_uses_shared_db(self, temp_db):
        """Audit repository should use the shared database path."""
        from app.services.audit_repository import AuditRepository
        
        repo = AuditRepository(db_path=temp_db)
        
        # Verify table exists in shared db
        from app.services.database import get_connection
        with get_connection(temp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_entries'"
            ).fetchone()
            assert tables is not None
    
    def test_all_tables_in_single_db(self, temp_db):
        """All tables should exist in the same database file."""
        from app.services.rate_limiter_sqlite import RateLimiterSQLite
        from app.services.audit_repository import AuditRepository
        
        # Initialize both services with same db
        limiter = RateLimiterSQLite(db_path=temp_db)
        repo = AuditRepository(db_path=temp_db)
        limiter.close()
        
        # Verify all tables exist in same db
        from app.services.database import get_connection
        with get_connection(temp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t[0] for t in tables]
            
            # Rate limiter tables
            assert 'api_calls' in table_names
            assert 'api_limited' in table_names
            
            # Audit tables
            assert 'audit_entries' in table_names
            assert 'audit_changes' in table_names
    
    def test_default_db_path_is_consistent(self):
        """Both services should use same default path."""
        from app.services.database import get_db_path, DEFAULT_DB_PATH
        from app.services.rate_limiter_sqlite import DEFAULT_DB_PATH as RATE_LIMIT_PATH
        from app.services.audit_repository import DEFAULT_DB_PATH as AUDIT_PATH
        
        # All should resolve to the same path
        assert str(DEFAULT_DB_PATH) == str(RATE_LIMIT_PATH)
        assert str(DEFAULT_DB_PATH) == str(AUDIT_PATH)
