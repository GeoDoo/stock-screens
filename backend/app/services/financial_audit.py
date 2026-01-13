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
        self.input_provenance = {}

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
        working_capital = self.extractor.working_capital()
        retained_earnings = self.extractor.retained_earnings()

        # GROUND TRUTH FIX: If Market Cap is 0 (API failed), try calculating from File-sourced shares + Profile price
        if not market_cap:
            shares = self.extractor.shares_outstanding()
            price = self.extractor.profile.get("price")
            if shares and price:
                market_cap = shares * price
                self.input_provenance["market_cap"] = {
                    "source": "calculated",
                    "description": "Reconstructed from filing-sourced shares and current price",
                    "confidence": "high"
                }
                logger.info("altman_z_score_market_cap_reconstructed", ticker=self.extractor.profile.get("symbol"), market_cap=market_cap)

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

    def _get_tax_rate_with_fallback(self) -> float:
        """Get tax rate with explicit fallback and provenance tracking."""
        rate, prov = self.extractor.tax_rate_with_provenance()
        if rate is None:
            rate = 0.25
            self.input_provenance["tax_rate"] = {
                "source": "fallback",
                "description": "Standard 25% corporate tax rate fallback (used when historical data is missing or invalid)",
                "confidence": "low"
            }
        else:
            self.input_provenance["tax_rate"] = {
                "source": prov.source,
                "description": prov.description,
                "confidence": prov.confidence
            }
        return rate

    def roic(self) -> Optional[float]:
        """
        Return on Invested Capital (ROIC) = NOPAT / Net Operating Assets.
        
        NOPAT = Operating Income * (1 - Tax Rate)
        Invested Capital = (Total Assets - Cash) - (Total Liabilities - Debt)
        """
        ebit = self.extractor.latest_operating_income()
        tax_rate = self._get_tax_rate_with_fallback()
        invested_capital = self.extractor.net_operating_assets()
        
        if ebit is None or invested_capital is None or invested_capital <= 0:
            return None
            
        nopat = ebit * (1 - tax_rate)
        return nopat / invested_capital

    def rotic(self) -> Optional[float]:
        """
        Return on Tangible Invested Capital (ROTIC) = NOPAT / Tangible Invested Capital.
        
        Excludes Goodwill and Intangibles from the denominator. This measures 
        the efficiency of the core tangible business, ignoring historical 
        acquisition premiums.
        """
        ebit = self.extractor.latest_operating_income()
        tax_rate = self._get_tax_rate_with_fallback()
        tangible_ic = self.extractor.tangible_invested_capital()
        
        if ebit is None or tangible_ic is None or tangible_ic <= 0:
            return None
            
        nopat = ebit * (1 - tax_rate)
        return nopat / tangible_ic

    def calculate_ratios(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Calculate comprehensive financial ratios."""
        
        # 1. Liquidity
        current_assets = self.extractor.current_assets()
        current_liabilities = self.extractor.total_current_liabilities()
        cash = self.extractor.cash()
        inventory = self.extractor.inventory()
        
        liquidity = {
            "current_ratio": current_assets / current_liabilities if current_assets and current_liabilities else None,
            "quick_ratio": (current_assets - (inventory or 0)) / current_liabilities if current_assets and current_liabilities else None,
            "cash_ratio": cash / current_liabilities if cash and current_liabilities else None,
        }
        
        # 2. Solvency
        total_debt = self.extractor.total_debt()
        total_equity = self.extractor.total_equity()
        total_assets = self.extractor.total_assets()
        ebit = self.extractor.latest_operating_income()
        raw_interest = self.extractor._get_ttm(self.extractor.income_statement, "interestExpense")
        
        solvency = {
            "debt_to_equity": total_debt / total_equity if total_debt and total_equity else None,
            "debt_to_assets": total_debt / total_assets if total_debt and total_assets else None,
            "interest_coverage": ebit / raw_interest if ebit and raw_interest and raw_interest > 0 else None,
            "equity_multiplier": total_assets / total_equity if total_assets and total_equity else None,
        }
        revenue = self.extractor.latest_revenue()
        ar = self.extractor.accounts_receivable()
        ap = self.extractor.account_payables()
        cogs = self.extractor._get_ttm(self.extractor.income_statement, "costOfRevenue")
        
        # DSO = (AR / Revenue) * 365
        dso = (ar / revenue) * 365 if ar and revenue else None
        # DIO = (Inventory / COGS) * 365
        dio = (inventory / cogs) * 365 if inventory and cogs else None
        # DPO = (AP / COGS) * 365
        dpo = (ap / cogs) * 365 if ap and cogs else None
        
        efficiency = {
            "asset_turnover": revenue / total_assets if revenue and total_assets else None,
            "inventory_turnover": cogs / inventory if cogs and inventory else None,
            "days_sales_outstanding": dso,
            "days_inventory_outstanding": dio,
            "days_payable_outstanding": dpo,
            "cash_conversion_cycle": (dso or 0) + (dio or 0) - (dpo or 0) if dso is not None and dio is not None and dpo is not None else None,
        }
        
        # 4. Profitability
        gp = self.extractor.gross_profit()
        ni = self.extractor.net_income()
        
        profitability = {
            "gross_margin": gp / revenue if gp and revenue else None,
            "operating_margin": ebit / revenue if ebit and revenue else None,
            "net_margin": ni / revenue if ni and revenue else None,
            "roe": ni / total_equity if ni and total_equity else None,
            "roa": ni / total_assets if ni and total_assets else None,
            "roic": self.roic(),
            "rotic": self.rotic(),
            "fcf_conversion": self.extractor.free_cash_flow() / ni if ni and ni != 0 and self.extractor.free_cash_flow() else None,
        }
        
        return {
            "liquidity": liquidity,
            "solvency": solvency,
            "efficiency": efficiency,
            "profitability": profitability
        }

    def get_accounting_corrections(self) -> List[Dict[str, Any]]:
        """
        Identify necessary accounting 'corrections' to reach economic reality.
        
        Example: R&D capitalization, Operating Lease capitalization.
        """
        corrections = []
        
        # 1. R&D Capitalization (Economic reality: R&D is an investment, not an expense)
        # We capitalize R&D over 5 years (straight-line)
        rd_hist = self.extractor.get_full_history("income_statement", "researchAndDevelopment")
        if rd_hist and len(rd_hist) >= 5:
            # Simple version: Unamortized portion = 0.8*RD(-1) + 0.6*RD(-2) + 0.4*RD(-3) + 0.2*RD(-4)
            unamortized = (0.8 * rd_hist[-1]) + (0.6 * rd_hist[-2]) + (0.4 * rd_hist[-3]) + (0.2 * rd_hist[-4])
            # Amortization for current year = 1/5 of previous 5 years
            amortization = sum(rd_hist[-5:]) / 5
            
            rd_adjustment = rd_hist[-1] - amortization
            
            corrections.append({
                "name": "R&D Capitalization",
                "impact_on_ebit": rd_adjustment,
                "impact_on_assets": unamortized,
                "description": f"Treating R&D as a 5-year asset. Current R&D expense of ${rd_hist[-1]/1e6:.1f}M replaced by amortization of ${amortization/1e6:.1f}M."
            })
            
        # 2. SBC Adjustment (Treating SBC as a cash expense)
        sbc = self.extractor._get_ttm(self.extractor.cash_flow, "stockBasedCompensation")
        if sbc and sbc > 0:
            corrections.append({
                "name": "SBC Economic Reality",
                "impact_on_ebit": -sbc,
                "impact_on_assets": 0,
                "description": f"Treating Stock-Based Compensation (${sbc/1e6:.1f}M) as a real cash-equivalent expense. While non-cash, it is a real cost of dilution to shareholders."
            })

        # 3. Operating Lease Capitalization (if not already on balance sheet)
        # Note: ASC 842 already puts them on balance sheet, but we check if they are missing
        oper_leases = self.extractor._get_latest(self.extractor.balance_sheet, "operatingLeaseObligations")
        if not oper_leases:
            # Estimate if missing: Rent Expense * 7 (industry rule of thumb)
            # Rent is usually in SG&A, hard to extract precisely without LLM
            pass
            
        return corrections

    def analyze_statements(self) -> Dict[str, Any]:
        """Run comprehensive quantitative audit."""
        sloan = self.sloan_ratio()
        z_score = self.altman_z_score()
        m_score = self.beneish_m_score()
        ratios = self.calculate_ratios()
        corrections = self.get_accounting_corrections()
        
        # Source variables for multiple checks
        net_income = self.extractor.net_income()
        ocf = self.extractor.cash_flow_from_operations()
        total_assets = self.extractor.total_assets()

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

        # 4. Revenue Quality
        # DSO check
        dso = ratios["efficiency"].get("days_sales_outstanding")
        if dso and dso > 90:
            findings.append(f"Revenue Quality: Days Sales Outstanding (DSO) of {dso:.0f} days is high. Risk of aggressive revenue recognition or collection issues.")
            
        # AR vs Revenue Growth (More robust check)
        revenue_hist = self.extractor.revenue_history()
        ar_hist = self.extractor.get_full_history("balance_sheet", "netReceivables")
        if len(revenue_hist) >= 2 and len(ar_hist) >= 2:
            rev_growth = (revenue_hist[-1] / revenue_hist[-2]) - 1
            ar_growth = (ar_hist[-1] / ar_hist[-2]) - 1
            if ar_growth > rev_growth + 0.15 and rev_growth > 0:
                findings.append(f"Revenue Quality: Accounts Receivable grew {ar_growth:.1%} vs Revenue growth of {rev_growth:.1%}. Possible 'channel stuffing'.")

        # 5. Asset Bloat: Other Assets + Intangibles vs Revenue
        intangibles = (self.extractor.goodwill() or 0) + (self.extractor.intangible_assets() or 0)
        if total_assets and total_assets > 0 and intangibles / total_assets > 0.40: # 40% of assets are 'soft'
            findings.append(f"Asset Bloat: Intangibles & Goodwill represent {intangibles/total_assets:.1%} of total assets. High impairment risk.")

        # 6. Capitalization Creep: CapEx vs Depreciation
        capex_hist = self.extractor.capex_history()
        da_hist = self.extractor.da_history()
        if capex_hist and da_hist and len(capex_hist) > 0 and len(da_hist) > 0:
            capex_to_da = capex_hist[-1] / da_hist[-1] if da_hist[-1] > 0 else 0
            if capex_to_da > 2.5: # Spending way more than replacing
                findings.append(f"CapEx Intensity: CapEx is {capex_to_da:.1f}x Depreciation. Potential 'capitalization creep' (hiding expenses).")
            elif capex_to_da < 0.7 and capex_to_da > 0: # Underinvesting
                findings.append(f"Underinvestment: CapEx is only {capex_to_da:.1f}x Depreciation. Firm may be under-investing in its core assets.")

        # 7. Solvency: Debt to EBITDA (Proxy)
        ebit = self.extractor.latest_operating_income()
        da = self.extractor._get_ttm(self.extractor.cash_flow, "depreciationAndAmortization") or 0
        ebitda = (ebit or 0) + da
        total_debt = self.extractor.total_debt()
        if ebitda > 0 and total_debt:
            debt_to_ebitda = total_debt / ebitda
            if debt_to_ebitda > 4.0:
                findings.append(f"Solvency Risk: Net Debt / EBITDA of {debt_to_ebitda:.1f}x is high. Standard covenant thresholds are often 3.0x - 4.0x.")

        # 8. Dilution Risk (SBC)
        sbc_val = self.extractor._get_ttm(self.extractor.cash_flow, "stockBasedCompensation")
        if sbc_val and ocf and ocf > 0:
            sbc_ratio = sbc_val / ocf
            if sbc_ratio > 0.15: # 15% of OCF is SBC
                findings.append(f"Dilution Risk: Stock-Based Comp represents {sbc_ratio:.1%} of Operating Cash Flow. High economic cost masked as 'non-cash'.")
        
        # 9. Capital Efficiency (ROTIC)
        rotic_val = self.rotic()
        if rotic_val:
            if rotic_val < 0.10: # 10% threshold
                findings.append(f"Capital Efficiency: ROTIC of {rotic_val:.1%} is below the 10% hurdle. The core tangible business may not be earning its cost of capital.")
            elif rotic_val > 0.40: # High efficiency
                findings.append(f"Capital Efficiency: Exceptional ROTIC of {rotic_val:.1%}. The core business has very high returns on tangible capital.")

        return {
            "sloan_ratio": sloan,
            "altman_z_score": z_score,
            "beneish_m_score": m_score,
            "liquidity_ratios": ratios["liquidity"],
            "solvency_ratios": ratios["solvency"],
            "efficiency_ratios": ratios["efficiency"],
            "profitability_ratios": ratios["profitability"],
            "accounting_corrections": corrections,
            "quantitative_findings": findings,
            "input_provenance": self.input_provenance
        }
