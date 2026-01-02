"""Stock screening and filtering service."""

from decimal import Decimal
from typing import Any

from app.models.stock import Stock


# Predefined screen definitions
PREDEFINED_SCREENS = {
    "graham_defensive": {
        "name": "Graham Defensive Investor",
        "description": "Benjamin Graham's criteria for defensive investors",
        "filters": [
            {"field": "pe_ratio", "operator": "<", "value": 15},
            {"field": "pb_ratio", "operator": "<", "value": 1.5},
            {"field": "current_ratio", "operator": ">", "value": 2},
            {"field": "eps", "operator": ">", "value": 0},
        ],
    },
    "graham_enterprising": {
        "name": "Graham Enterprising Investor",
        "description": "Less strict criteria for active value investors",
        "filters": [
            {"field": "pe_ratio", "operator": "<", "value": 20},
            {"field": "pb_ratio", "operator": "<", "value": 2.5},
            {"field": "current_ratio", "operator": ">", "value": 1.5},
            {"field": "eps", "operator": ">", "value": 0},
        ],
    },
    "low_debt_high_roe": {
        "name": "Low Debt, High ROE",
        "description": "Quality companies with strong returns and low leverage",
        "filters": [
            {"field": "debt_to_equity", "operator": "<", "value": 0.5},
            {"field": "roe", "operator": ">", "value": 15},
        ],
    },
    "deep_value": {
        "name": "Deep Value",
        "description": "Extremely cheap stocks by multiple metrics",
        "filters": [
            {"field": "pe_ratio", "operator": "<", "value": 10},
            {"field": "pb_ratio", "operator": "<", "value": 1},
        ],
    },
}


class ScreeningService:
    """Service for filtering and screening stocks."""

    OPERATORS = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    def apply_filters(
        self,
        stocks: list[Stock],
        filters: list[dict],
    ) -> list[Stock]:
        """
        Apply custom filters to a list of stocks.
        
        Args:
            stocks: List of stocks to filter
            filters: List of filter conditions, each with:
                - field: Name of the field to filter on
                - operator: Comparison operator (<, <=, >, >=, ==, !=)
                - value: Value to compare against
        
        Returns:
            Filtered list of stocks
        """
        result = []
        
        for stock in stocks:
            if self._stock_passes_filters(stock, filters):
                result.append(stock)
        
        return result

    def _stock_passes_filters(self, stock: Stock, filters: list[dict]) -> bool:
        """Check if a stock passes all filters."""
        for f in filters:
            field = f["field"]
            operator = f["operator"]
            value = Decimal(str(f["value"]))
            
            # Get the field value from fundamentals
            if stock.fundamentals is None:
                return False
            
            stock_value = getattr(stock.fundamentals, field, None)
            if stock_value is None:
                return False
            
            # Apply operator
            op_func = self.OPERATORS.get(operator)
            if not op_func:
                raise ValueError(f"Unknown operator: {operator}")
            
            if not op_func(stock_value, value):
                return False
        
        return True

    def apply_predefined_screen(
        self,
        stocks: list[Stock],
        screen_name: str,
    ) -> list[Stock]:
        """
        Apply a predefined screen to stocks.
        
        Args:
            stocks: List of stocks to screen
            screen_name: Name of the predefined screen
        
        Returns:
            Filtered list of stocks matching the screen criteria
        """
        if screen_name not in PREDEFINED_SCREENS:
            raise ValueError(f"Unknown screen: {screen_name}")
        
        screen = PREDEFINED_SCREENS[screen_name]
        return self.apply_filters(stocks, screen["filters"])

    def get_available_screens(self) -> list[dict]:
        """Return list of available predefined screens."""
        return [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in PREDEFINED_SCREENS.items()
        ]

