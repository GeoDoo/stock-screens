"""
Unit tests for stock screening/filtering logic.

TDD: Writing tests ONE AT A TIME.
"""

import pytest
from decimal import Decimal

from app.services.screening import ScreeningService
from app.models.stock import Stock, StockFundamentals


class TestCustomFilters:
    """Tests for custom filter application."""

    def test_filter_by_pe_ratio(self):
        """
        Test filtering stocks by P/E ratio.
        
        Filter: PE < 15
        """
        service = ScreeningService()
        
        stocks = [
            _make_stock("LOW", pe=Decimal("10")),
            _make_stock("MID", pe=Decimal("15")),
            _make_stock("HIGH", pe=Decimal("25")),
        ]
        
        filters = [{"field": "pe_ratio", "operator": "<", "value": 15}]
        
        result = service.apply_filters(stocks, filters)
        
        assert len(result) == 1
        assert result[0].symbol == "LOW"


class TestPredefinedScreens:
    """Tests for predefined value screens."""

    def test_graham_defensive_screen(self):
        """
        Test Graham's Defensive Investor criteria:
        - P/E < 15
        - P/B < 1.5
        - Current Ratio > 2
        - Positive earnings
        """
        service = ScreeningService()
        
        stocks = [
            _make_stock("GOOD", pe=Decimal("10"), pb=Decimal("1.2"), 
                       current_ratio=Decimal("2.5"), eps=Decimal("5")),
            _make_stock("BADPE", pe=Decimal("20"), pb=Decimal("1.2"),
                       current_ratio=Decimal("2.5"), eps=Decimal("5")),
            _make_stock("BADPB", pe=Decimal("10"), pb=Decimal("2.0"),
                       current_ratio=Decimal("2.5"), eps=Decimal("5")),
        ]
        
        result = service.apply_predefined_screen(stocks, "graham_defensive")
        
        assert len(result) == 1
        assert result[0].symbol == "GOOD"


def _make_stock(
    symbol: str,
    pe: Decimal = None,
    pb: Decimal = None,
    current_ratio: Decimal = None,
    eps: Decimal = None,
) -> Stock:
    """Helper to create test stocks."""
    return Stock(
        symbol=symbol,
        name=f"{symbol} Corp",
        fundamentals=StockFundamentals(
            pe_ratio=pe,
            pb_ratio=pb,
            current_ratio=current_ratio,
            eps=eps,
        ),
    )

