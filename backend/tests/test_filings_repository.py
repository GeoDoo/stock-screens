"""Tests for SEC filings PDF caching repository."""
import tempfile
from datetime import date, datetime, timezone

import pytest

from app.services.filings_repository import (
    FilingsRepository,
    CachedFiling,
)


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name


@pytest.fixture
def repo(temp_db):
    """Create a repository instance with temp database."""
    return FilingsRepository(db_path=temp_db)


class TestFilingsRepository:
    """Tests for FilingsRepository."""

    def test_init_creates_tables(self, repo, temp_db):
        """Repository should create necessary tables on init."""
        import sqlite3
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='filing_pdfs'"
        )
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == "filing_pdfs"

    def test_save_and_get_pdf(self, repo):
        """Should save and retrieve a PDF."""
        pdf_data = b"test pdf content" * 100  # ~1.6KB
        
        cached = repo.save_pdf(
            ticker="AAPL",
            cik="0000320193",
            accession_number="0000320193-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            document_name="aapl-20240115.htm",
            pdf_data=pdf_data,
        )
        
        assert cached.id > 0
        assert cached.ticker == "AAPL"
        assert cached.cik == "0000320193"
        assert cached.accession_number == "0000320193-24-000001"
        assert cached.form_type == "10-K"
        assert cached.filing_date == date(2024, 1, 15)
        assert cached.document_name == "aapl-20240115.htm"
        assert cached.pdf_size_kb == len(pdf_data) // 1024
        
        # Retrieve it
        retrieved = repo.get_pdf(
            cik="0000320193",
            accession_number="0000320193-24-000001",
            document_name="aapl-20240115.htm",
        )
        
        assert retrieved == pdf_data

    def test_get_pdf_not_found(self, repo):
        """Should return None for non-existent PDF."""
        result = repo.get_pdf(
            cik="0000000000",
            accession_number="0000000000-00-000000",
            document_name="notfound.htm",
        )
        
        assert result is None

    def test_save_pdf_replaces_existing(self, repo):
        """Saving a PDF with same identifiers should replace the old one."""
        pdf_data_v1 = b"version 1" * 100
        pdf_data_v2 = b"version 2 updated" * 100
        
        # Save v1
        repo.save_pdf(
            ticker="MSFT",
            cik="0000789019",
            accession_number="0000789019-24-000001",
            form_type="10-Q",
            filing_date=date(2024, 3, 1),
            document_name="msft-20240301.htm",
            pdf_data=pdf_data_v1,
        )
        
        # Save v2 with same identifiers
        repo.save_pdf(
            ticker="MSFT",
            cik="0000789019",
            accession_number="0000789019-24-000001",
            form_type="10-Q",
            filing_date=date(2024, 3, 1),
            document_name="msft-20240301.htm",
            pdf_data=pdf_data_v2,
        )
        
        # Should get v2
        retrieved = repo.get_pdf(
            cik="0000789019",
            accession_number="0000789019-24-000001",
            document_name="msft-20240301.htm",
        )
        
        assert retrieved == pdf_data_v2

    def test_list_cached(self, repo):
        """Should list cached filings without PDF data."""
        # Save a few PDFs
        for i, ticker in enumerate(["AAPL", "MSFT", "AAPL"]):
            repo.save_pdf(
                ticker=ticker,
                cik=f"000000000{i}",
                accession_number=f"000000000{i}-24-000001",
                form_type="10-K" if i % 2 == 0 else "10-Q",
                filing_date=date(2024, 1 + i, 15),
                document_name=f"test-{i}.htm",
                pdf_data=b"data" * 100,
            )
        
        # List all
        all_cached = repo.list_cached()
        assert len(all_cached) == 3
        
        # List by ticker
        aapl_cached = repo.list_cached(ticker="AAPL")
        assert len(aapl_cached) == 2
        
        # List by form type
        tenk_cached = repo.list_cached(form_type="10-K")
        assert len(tenk_cached) == 2
        
        # Verify PDF data is empty in list view
        for cached in all_cached:
            assert cached.pdf_data == b""

    def test_delete_pdf(self, repo):
        """Should delete a cached PDF."""
        repo.save_pdf(
            ticker="NVDA",
            cik="0001045810",
            accession_number="0001045810-24-000001",
            form_type="8-K",
            filing_date=date(2024, 2, 1),
            document_name="nvda-8k.htm",
            pdf_data=b"test data" * 100,
        )
        
        # Delete it
        deleted = repo.delete_pdf(
            cik="0001045810",
            accession_number="0001045810-24-000001",
            document_name="nvda-8k.htm",
        )
        
        assert deleted is True
        
        # Should not find it
        result = repo.get_pdf(
            cik="0001045810",
            accession_number="0001045810-24-000001",
            document_name="nvda-8k.htm",
        )
        
        assert result is None

    def test_delete_pdf_not_found(self, repo):
        """Delete should return False for non-existent PDF."""
        deleted = repo.delete_pdf(
            cik="0000000000",
            accession_number="0000000000-00-000000",
            document_name="notfound.htm",
        )
        
        assert deleted is False

    def test_get_cache_stats(self, repo):
        """Should return cache statistics."""
        # Empty cache
        stats = repo.get_cache_stats()
        assert stats["total_files"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["unique_tickers"] == 0
        
        # Add some data
        for i, ticker in enumerate(["AAPL", "MSFT", "AAPL"]):
            repo.save_pdf(
                ticker=ticker,
                cik=f"000000000{i}",
                accession_number=f"000000000{i}-24-000001",
                form_type="10-K" if i == 0 else "10-Q",
                filing_date=date(2024, 1 + i, 15),
                document_name=f"test-{i}.htm",
                pdf_data=b"x" * 1024 * 100,  # 100KB each
            )
        
        stats = repo.get_cache_stats()
        assert stats["total_files"] == 3
        assert stats["unique_tickers"] == 2  # AAPL and MSFT
        assert stats["unique_form_types"] == 2  # 10-K and 10-Q
        assert stats["total_size_mb"] > 0

    def test_clear_cache_all(self, repo):
        """Should clear all cached PDFs."""
        # Add some data
        for i in range(3):
            repo.save_pdf(
                ticker="TEST",
                cik=f"000000000{i}",
                accession_number=f"000000000{i}-24-000001",
                form_type="10-K",
                filing_date=date(2024, 1, 15),
                document_name=f"test-{i}.htm",
                pdf_data=b"data" * 100,
            )
        
        assert repo.get_cache_stats()["total_files"] == 3
        
        deleted = repo.clear_cache()
        
        assert deleted == 3
        assert repo.get_cache_stats()["total_files"] == 0


class TestCachedFiling:
    """Tests for CachedFiling dataclass."""

    def test_document_url_property(self):
        """Should construct correct SEC document URL."""
        filing = CachedFiling(
            id=1,
            ticker="AAPL",
            cik="0000320193",
            accession_number="0000320193-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            document_name="aapl-20240115.htm",
            pdf_data=b"",
            pdf_size_kb=100,
            created_at=datetime.now(timezone.utc),
        )
        
        # Accession "0000320193-24-000001" becomes "000032019324000001" (dashes removed)
        expected = (
            "https://www.sec.gov/Archives/edgar/data/"
            "320193/000032019324000001/aapl-20240115.htm"
        )
        assert filing.document_url == expected
