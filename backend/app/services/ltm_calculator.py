"""
LTM (Last Twelve Months) Calculator for SEC Filings.

Institutional-grade forensic analysis requires continuous 12-month periods
even when analyzing quarterly (10-Q) filings. This service merges facts
across multiple filings to construct a true LTM view.
"""
import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = structlog.get_logger(__name__)

class LTMCalculator:
    """
    Calculates LTM (Trailing Twelve Months) values by merging facts
    from current 10-Q, previous 10-K, and previous year's matching 10-Q.
    
    Formula: LTM = Current_YTD + Previous_FY - Previous_YTD
    """
    
    # Concepts that should be summed for LTM (flow items)
    FLOW_CONCEPTS = [
        "revenue", "net_income", "operating_cash_flow", "capex",
        "gross_profit", "operating_income", "ebit", "interest_expense",
        "tax_expense", "ebt", "cost_of_revenue", "da", "sbc", "dividends",
        "research_and_development"
    ]
    
    # Concepts that are point-in-time (balance sheet items)
    INSTANT_CONCEPTS = [
        "total_assets", "total_liabilities", "equity", "total_debt",
        "current_assets", "current_liabilities", "inventory", "accounts_receivable",
        "retained_earnings", "ppe_net", "cash", "goodwill", "intangibles",
        "short_term_debt", "long_term_debt", "accounts_payable",
        "minority_interest", "preferred_stock", "deferred_tax_assets",
        "pension_liability", "investments"
    ]

    def calculate_ltm_facts(
        self, 
        current_facts: List[Dict[str, Any]], 
        previous_fy_facts: List[Dict[str, Any]],
        previous_ytd_facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge facts to create a single LTM fact set.
        
        Args:
            current_facts: Facts from the latest filing (e.g., Q3 2025)
            previous_fy_facts: Facts from the last fiscal year (e.g., FY 2024)
            previous_ytd_facts: Facts from last year's matching period (e.g., Q3 2024)
            
        Returns:
            A dictionary of LTM facts.
        """
        ltm_facts = {}
        
        # 1. Latest date and duration
        latest_period = self._get_latest_flow_period(current_facts)
        if not latest_period:
            logger.warning("ltm_calc_no_current_flow_period")
            return {}
            
        ltm_facts["date"] = latest_period["date"]
        ltm_facts["duration"] = 365 # It's an LTM period
        ltm_facts["is_ltm"] = True
        
        # 2. Handle Instant concepts (always take latest available)
        latest_instant = self._get_latest_instant_period(current_facts)
        if latest_instant:
            for concept in self.INSTANT_CONCEPTS:
                if concept in latest_instant:
                    ltm_facts[concept] = latest_instant[concept]
        
        # 3. Handle Flow concepts (the actual LTM math)
        # Find the best periods for math
        curr_ytd = latest_period
        prev_fy = self._get_fy_period(previous_fy_facts)
        prev_ytd = self._get_matching_ytd_period(previous_ytd_facts, curr_ytd["duration"])
        
        if not all([curr_ytd, prev_fy, prev_ytd]):
            logger.warning("ltm_calc_missing_periods", 
                         has_curr=bool(curr_ytd), 
                         has_prev_fy=bool(prev_fy), 
                         has_prev_ytd=bool(prev_ytd))
            # Fallback: if we can't do math, just take current YTD and flag it
            for concept in self.FLOW_CONCEPTS:
                if concept in curr_ytd:
                    ltm_facts[concept] = curr_ytd[concept]
            ltm_facts["is_partial_ltm"] = True
            return ltm_facts

        for concept in self.FLOW_CONCEPTS:
            val_curr = curr_ytd.get(concept)
            val_fy = prev_fy.get(concept)
            val_prev_ytd = prev_ytd.get(concept)
            
            if val_curr is not None and val_fy is not None and val_prev_ytd is not None:
                # LTM = Current YTD + Previous FY - Previous YTD
                ltm_facts[concept] = val_curr + val_fy - val_prev_ytd
            elif val_curr is not None:
                # Fallback to current YTD if math fails for this specific concept
                ltm_facts[concept] = val_curr
                
        return ltm_facts

    def _get_latest_flow_period(self, facts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # Sort by date desc, then duration desc (prefer YTD over Q)
        flow_periods = [f for f in facts if f.get("duration", 0) > 0]
        if not flow_periods:
            return None
        sorted_periods = sorted(flow_periods, key=lambda x: (x["date"], x["duration"]), reverse=True)
        return sorted_periods[0]

    def _get_latest_instant_period(self, facts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        instant_periods = [f for f in facts if f.get("duration") == 0]
        if not instant_periods:
            return None
        sorted_periods = sorted(instant_periods, key=lambda x: x["date"], reverse=True)
        return sorted_periods[0]

    def _get_fy_period(self, facts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # Find period with duration ~365 days
        fy_periods = [f for f in facts if 350 <= (f.get("duration") or 0) <= 375]
        if not fy_periods:
            return None
        return sorted(fy_periods, key=lambda x: x["date"], reverse=True)[0]

    def _get_matching_ytd_period(self, facts: List[Dict[str, Any]], target_duration: int) -> Optional[Dict[str, Any]]:
        # Find period with similar duration (+/- 10 days)
        matching = [f for f in facts if abs((f.get("duration") or 0) - target_duration) <= 10]
        if not matching:
            return None
        return sorted(matching, key=lambda x: x["date"], reverse=True)[0]
