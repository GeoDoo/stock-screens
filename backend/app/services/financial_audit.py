from typing import List, Optional, Dict, Any
from app.services.data_extractor import DataExtractor
from app.services.logging_config import logger

class FinancialAuditService:
    """
    Performs quantitative forensic analysis on financial statements.
    
    Identifies accounting shenanigans, earnings quality issues, 
    and bankruptcy/fraud risks using established models (Altman, Beneish, Sloan).
    """

    def __init__(self, extractor: DataExtractor):
        self.extractor = extractor

    def sloan_ratio(self) -> Optional[float]:
        """
        Sloan Ratio = (Net Income - Cash Flow from Operations) / Total Assets.
        
        High Sloan Ratio (> 0.10) indicates high accruals, meaning 
        net income is significantly higher than cash generated.
        This is a primary red flag for earnings quality.
        """
        net_income = self.extractor.net_income()
        ocf = self.extractor.cash_flow_from_operations()
        total_assets = self.extractor.total_assets()

        if net_income is None or ocf is None or not total_assets:
            return None
        
        return (net_income - ocf) / total_assets

    def altman_z_score(self) -> Optional[dict]:
        """
        Altman Z-Score for public manufacturing firms (Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E).
        
        A = Working Capital / Total Assets
        B = Retained Earnings / Total Assets
        C = EBIT / Total Assets
        D = Market Cap / Total Liabilities
        E = Sales / Total Assets
        
        Zones:
        - Z > 2.99: Safe Zone
        - 1.81 < Z < 2.99: Gray Zone
        - Z < 1.81: Distress Zone (High Bankruptcy Risk)
        """
        total_assets = self.extractor.total_assets()
        total_liabilities = self.extractor.total_liabilities()
        market_cap = self.extractor.market_cap()
        revenue = self.extractor.latest_revenue()
        ebit = self.extractor.latest_operating_income()
        working_capital = self.extractor.latest_working_capital()
        retained_earnings = self.extractor.retained_earnings()

        if not all([total_assets, total_liabilities, market_cap, revenue, ebit, working_capital]) or total_assets == 0:
            return None

        # Components
        a = working_capital / total_assets
        b = (retained_earnings or 0) / total_assets
        c = ebit / total_assets
        d = market_cap / total_liabilities
        e = revenue / total_assets

        z_score = (1.2 * a) + (1.4 * b) + (3.3 * c) + (0.6 * d) + (1.0 * e)

        zone = "Safe"
        if z_score < 1.81:
            zone = "Distress"
        elif z_score < 2.99:
            zone = "Gray"

        return {
            "score": z_score,
            "zone": zone,
            "components": {"A": a, "B": b, "C": c, "D": d, "E": e}
        }

    def beneish_m_score(self) -> Optional[dict]:
        """
        Beneish M-Score for detecting earnings manipulation.
        
        Simplifed version using 8 variables. 
        M-Score > -1.78 suggests a high probability of manipulation.
        """
        # Note: This requires prior year data.
        revenue_hist = self.extractor.revenue_history()
        receivables_hist = self.extractor.get_full_history("balance_sheet", "netReceivables")
        gross_margin_hist = self.extractor.get_full_history("income_statement", "grossProfitRatio")
        aqi_hist = [] # Asset Quality Index
        
        # We need at least 2 years of history
        if len(revenue_hist) < 2:
            return None

        # Current vs Prior Year
        rev_curr, rev_prev = revenue_hist[-1], revenue_hist[-2]
        rec_curr = self.extractor.accounts_receivable()
        rec_prev = receivables_hist[-2] if len(receivables_hist) >= 2 else None
        
        if not all([rev_curr, rev_prev, rec_curr, rec_prev]) or rev_prev == 0:
            return None

        # DSRI (Days Sales in Receivables Index)
        dsri = (rec_curr / rev_curr) / (rec_prev / rev_prev) if rec_prev and rev_prev else 1.0
        
        # GMI (Gross Margin Index)
        gmi = 1.0
        if len(gross_margin_hist) >= 2:
            gm_curr, gm_prev = gross_margin_hist[-1], gross_margin_hist[-2]
            if gm_curr and gm_prev:
                gmi = gm_prev / gm_curr

        # SGI (Sales Growth Index)
        sgi = rev_curr / rev_prev

        # Simplified M-Score (Probabilistic)
        m_score = -4.84 + (0.92 * dsri) + (0.528 * gmi) + (0.404 * sgi)
        
        is_manipulator = m_score > -1.78

        return {
            "score": m_score,
            "is_potential_manipulator": is_manipulator,
            "dsri": dsri,
            "gmi": gmi,
            "sgi": sgi
        }

    def analyze_statements(self) -> Dict[str, Any]:
        """Run comprehensive quantitative audit."""
        sloan = self.sloan_ratio()
        z_score = self.altman_z_score()
        m_score = self.beneish_m_score()

        findings = []
        
        # 1. Sloan Ratio (Accruals)
        if sloan and sloan > 0.10:
            findings.append(f"High Accrual Risk: Sloan Ratio of {sloan:.1%} indicates net income may not be supported by cash flow.")
        
        # 2. Altman Z-Score (Bankruptcy)
        if z_score and z_score["zone"] == "Distress":
            findings.append(f"Bankruptcy Risk: Altman Z-Score of {z_score['score']:.2f} is in the Distress Zone.")
            
        # 3. Beneish M-Score (Manipulation)
        if m_score and m_score["is_potential_manipulator"]:
            findings.append(f"Earnings Quality: Beneish M-Score of {m_score['score']:.2f} indicates potential earnings manipulation.")

        # 4. Revenue Quality: AR vs Revenue Growth
        revenue_hist = self.extractor.revenue_history()
        ar_hist = self.extractor.get_full_history("balance_sheet", "netReceivables")
        if len(revenue_hist) >= 2 and len(ar_hist) >= 2:
            rev_growth = (revenue_hist[-1] / revenue_hist[-2]) - 1
            ar_growth = (ar_hist[-1] / ar_hist[-2]) - 1
            if ar_growth > rev_growth + 0.15: # 15% divergence
                findings.append(f"Revenue Quality: Accounts Receivable grew {ar_growth:.1%} vs Revenue growth of {rev_growth:.1%}. Potential 'channel stuffing'.")

        # 5. Asset Bloat: Other Assets + Intangibles vs Revenue
        intangibles = self.extractor.goodwill() or 0 + (self.extractor.intangible_assets() or 0)
        total_assets = self.extractor.total_assets()
        if total_assets and intangibles / total_assets > 0.40: # 40% of assets are 'soft'
            findings.append(f"Asset Bloat: Intangibles & Goodwill represent {intangibles/total_assets:.1%} of total assets. High impairment risk.")

        # 6. Capitalization Creep: CapEx vs Depreciation
        capex_hist = self.extractor.capex_history()
        da_hist = self.extractor.da_history()
        if capex_hist and da_hist:
            capex_to_da = capex_hist[-1] / da_hist[-1] if da_hist[-1] > 0 else 0
            if capex_to_da > 2.5: # Spending way more than replacing
                findings.append(f"CapEx Intensity: CapEx is {capex_to_da:.1f}x Depreciation. Verify if this is growth or 'capitalization creep' (hiding expenses).")
            elif capex_to_da < 0.7 and capex_to_da > 0: # Underinvesting
                findings.append(f"Underinvestment: CapEx is only {capex_to_da:.1f}x Depreciation. Firm may be liquidating assets to boost cash flow.")

        # 8. SBC Analysis (Dilution Risk)
        # SBC is a non-cash expense, but a real economic cost (dilution)
        # We need to extract SBC from the cash flow statement
        sbc_val = self.extractor.cash_flow[0].get("stockBasedCompensation") if self.extractor.cash_flow else None
        if sbc_val and ocf:
            sbc_ratio = sbc_val / ocf
            if sbc_ratio > 0.15: # 15% of OCF is SBC
                findings.append(f"Dilution Risk: Stock-Based Comp represents {sbc_ratio:.1%} of Operating Cash Flow. High economic cost masked as 'non-cash'.")

        # 9. Asset Quality Index (AQI)
        # AQI = 1 - (Current Assets + PPE) / Total Assets
        # High AQI means more 'soft' assets (deferred costs, etc.)
        total_assets = self.extractor.total_assets()
        current_assets = self.extractor.current_assets()
        ppe = self.extractor.ppe()
        if total_assets and current_assets is not None and ppe is not None:
            aqi = 1 - (current_assets + ppe) / total_assets
            if aqi > 0.30: # > 30% are 'soft' assets
                findings.append(f"Asset Quality: {aqi:.1%} of assets are 'soft' (non-current, non-PPE). Potential cost deferral or inflated balance sheet.")

        # 10. Accrual Ratio (Institutional Sloan)
        # Accrual Ratio = (NI - (OCF - Cash Dividends)) / Total Assets
        dividends = self.extractor.cash_flow[0].get("dividendsPaid") if self.extractor.cash_flow else 0
        if net_income is not None and ocf is not None and total_assets:
            accrual_ratio = (net_income - (ocf - abs(dividends or 0))) / total_assets
            if accrual_ratio > 0.15:
                findings.append(f"Aggressive Accruals: Accrual Ratio of {accrual_ratio:.1%} is high. Potential earnings manipulation.")

        # 7. Margin Integrity: Gross vs Operating Margin
        gross_margin_hist = self.extractor.get_full_history("income_statement", "grossProfitRatio")
        if len(gross_margin_hist) >= 2:
            ebit_curr = self.extractor.latest_operating_income()
            rev_curr = self.extractor.latest_revenue()
            if ebit_curr and rev_curr:
                op_margin_curr = ebit_curr / rev_curr
                gm_curr = gross_margin_hist[-1]
                # If operating margin is expanding while gross margin is flat/falling
                # it might mean R&D or SG&A cuts are masking a deteriorating core business
                gm_prev = gross_margin_hist[-2]
                if gm_curr < gm_prev and op_margin_curr > (gross_margin_hist[-2] * 0.5): # Simplified check
                     findings.append("Margin Integrity: Operating margins are expanding despite falling/flat gross margins. Possible aggressive cost cutting.")

        return {
            "sloan_ratio": sloan,
            "altman_z_score": z_score,
            "beneish_m_score": m_score,
            "quantitative_findings": findings
        }
