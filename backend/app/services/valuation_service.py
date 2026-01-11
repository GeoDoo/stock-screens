from typing import Optional, List, Dict
from datetime import datetime, timezone
from app.constants import DEFAULT_TAX_RATE
from app.services.stock_data_client import StockDataClient
from app.services.data_adapter import stock_data_to_legacy
from app.services.data_extractor import DataExtractor
from app.services.wacc_calculator import WACCCalculator
from app.services.fcf_projector import FCFProjector
from app.services.dcf_calculator import DCFCalculator
from app.services.sensitivity_calculator import SensitivityCalculator
from app.services.capital_efficiency import analyze_value_creation


class ValuationService:
    """
    Orchestrates the full DCF valuation:
    1. Fetch data from the specified provider
    2. Extract inputs using DataExtractor
    3. Calculate WACC
    4. Project FCF using FCFProjector
    5. Run DCF to get intrinsic value
    """
    
    # P2.8: Financial sectors/industries where DCF is less appropriate
    # These companies have different capital structures where the balance sheet
    # IS the business (banks lend deposits, insurers hold float, etc.)
    FINANCIAL_SECTORS = {"Financial Services", "Financials", "Financial"}
    FINANCIAL_INDUSTRIES = {
        "Banks—Regional", "Banks—Diversified", "Banks - Regional", "Banks - Diversified",
        "Insurance—Life", "Insurance—Property & Casualty", "Insurance—Diversified",
        "Insurance - Life", "Insurance - Property & Casualty", "Insurance - Diversified",
        "Insurance—Reinsurance", "Insurance - Reinsurance",
        "Asset Management", "Capital Markets",
        "Credit Services", "Mortgage Finance",
        "Savings & Cooperative Banks",
    }

    def __init__(self, client: StockDataClient):
        """
        Initialize with a configured StockDataClient.
        
        Args:
            client: StockDataClient configured with the user's chosen provider
        """
        self.client = client

    async def value_stock(
        self,
        symbol: str,
        projection_years: int = 5,
        terminal_growth_rate: float = 0.03,
        revenue_growth: Optional[float] = None,
        operating_margin: Optional[float] = None,
        market_risk_premium: Optional[float] = None,
        discount_rate_override: Optional[float] = None,
        # FCF projection ratios - pass from frontend for clean TTM/Annual separation
        da_ratio: Optional[float] = None,
        capex_ratio: Optional[float] = None,
        wc_ratio: Optional[float] = None,
        # Advanced DCF options
        use_mid_year_discounting: bool = False,
        wc_mode: str = "level",
        # Multi-stage growth - if provided, overrides revenue_growth
        growth_schedule: Optional[List[float]] = None,
        # Multi-stage economics schedules - for modeling maturing companies
        margin_schedule: Optional[List[float]] = None,
        da_schedule: Optional[List[float]] = None,
        capex_schedule: Optional[List[float]] = None,
        wc_schedule: Optional[List[float]] = None,
        # SBC dilution - annual share growth rate from stock-based compensation
        annual_dilution_rate: float = 0.0,
        # Exit Multiple cross-check - sector/peer median EV/EBITDA for comparison
        sector_ev_ebitda_multiple: Optional[float] = None,
    ) -> dict:
        """
        Perform full DCF valuation for a stock.
        
        Args:
            symbol: Stock ticker
            projection_years: Years to project (default 5)
            terminal_growth_rate: Perpetual growth rate (default 3%)
            revenue_growth: Override historical growth rate
            operating_margin: Override historical margin
            market_risk_premium: Override default 6%
            discount_rate_override: If set, use this instead of calculated WACC
        
        Returns:
            Dict with intrinsic value, WACC, projections, and inputs used
        """
        # Record data fetch timestamp for provenance
        data_fetched_at = datetime.now(timezone.utc).isoformat()
        
        # 1. Fetch data (with automatic provider fallback)
        stock_data = await self.client.get_stock_data(symbol)
        risk_free_rate = await self.client.get_treasury_rate()

        # 2. Convert to legacy format and extract inputs
        data = stock_data_to_legacy(stock_data)
        extractor = DataExtractor(data, market_risk_premium=market_risk_premium)
        
        # P2.8: Check for financial companies and generate warning
        business_type_warning = self._get_business_type_warning(
            sector=stock_data.profile.sector,
            industry=stock_data.profile.industry,
        )

        # 3. Calculate WACC (only if all required components are available)
        beta = extractor.beta()
        cost_of_debt = extractor.cost_of_debt(risk_free_rate=risk_free_rate)
        tax_rate = extractor.tax_rate()
        market_cap = extractor.market_cap()
        total_debt = extractor.total_debt()

        # Check if we can calculate WACC - requires beta, market_cap, and cost_of_debt
        can_calculate_wacc = (
            beta is not None and 
            market_cap is not None and market_cap > 0 and
            cost_of_debt is not None
        )
        
        calculated_wacc = None
        if can_calculate_wacc:
            wacc_calculator = WACCCalculator(
                risk_free_rate=risk_free_rate,
                beta=beta,
                market_risk_premium=extractor.market_risk_premium(),
                cost_of_debt=cost_of_debt,
                tax_rate=tax_rate if tax_rate is not None else DEFAULT_TAX_RATE,
                market_cap=market_cap,
                total_debt=total_debt if total_debt is not None else 0,
            )
            calculated_wacc = wacc_calculator.calculate()
        
        # Use custom discount rate if provided, otherwise use calculated WACC
        # If WACC couldn't be calculated and no custom rate, we can't proceed
        if discount_rate_override is not None:
            discount_rate = discount_rate_override
        elif calculated_wacc is not None:
            discount_rate = calculated_wacc
        else:
            raise ValueError("Cannot calculate WACC (missing beta, market cap, or cost of debt). Please provide a custom discount rate.")

        # CRITICAL GUARDRAIL: Discount rate must exceed terminal growth
        # Otherwise terminal value formula produces nonsense (negative or infinite)
        if discount_rate <= terminal_growth_rate:
            raise ValueError(
                f"Discount rate ({discount_rate:.2%}) must be greater than "
                f"terminal growth rate ({terminal_growth_rate:.2%}). "
                "This is a fundamental DCF constraint - otherwise terminal value is undefined."
            )

        # 4. Project FCF
        fcf_projector = FCFProjector(
            historical_revenue=extractor.revenue_history(),
            historical_ebit=extractor.ebit_history(),
            historical_da=extractor.da_history(),
            historical_capex=extractor.capex_history(),
            historical_working_capital=extractor.working_capital_history(),
            tax_rate=extractor.tax_rate() or 0.25,
        )

        projections = fcf_projector.project(
            years=projection_years,
            revenue_growth=revenue_growth,
            operating_margin=operating_margin,
            da_ratio=da_ratio,
            capex_ratio=capex_ratio,
            wc_ratio=wc_ratio,
            wc_mode=wc_mode,
            growth_schedule=growth_schedule,
            # Multi-stage economics schedules
            margin_schedule=margin_schedule,
            da_schedule=da_schedule,
            capex_schedule=capex_schedule,
            wc_schedule=wc_schedule,
        )

        # 5. Run DCF
        projected_fcf = [p["fcf"] for p in projections]
        
        # Mid-year discounting: assumes cash flows occur mid-year instead of year-end
        # This typically increases value by ~2-5% as cash flows are "closer"
        discount_offset = 0.5 if use_mid_year_discounting else 0.0
        
        # Use the projected FCFs directly instead of growth-based projection
        # Calculate PV of projected FCFs
        pv_fcf = sum(
            fcf / ((1 + discount_rate) ** (year - discount_offset))
            for year, fcf in enumerate(projected_fcf, start=1)
        )

        # Terminal value
        final_fcf = projected_fcf[-1]
        terminal_value = final_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        pv_terminal = terminal_value / ((1 + discount_rate) ** (projection_years - discount_offset))

        enterprise_value = pv_fcf + pv_terminal

        # Net debt adjustment
        total_debt = extractor.total_debt() or 0
        cash = extractor.cash() or 0
        net_debt = total_debt - cash
        
        # Institutional-grade Equity Bridge components
        minority_interest = extractor.minority_interest() or 0
        preferred_stock = extractor.preferred_stock() or 0
        deferred_tax_assets = extractor.deferred_tax_assets() or 0
        pension_deficit = extractor.pension_liability() or 0
        
        # Full Equity Bridge:
        # Equity = EV - Net Debt - Minority Interest - Preferred + NOLs - Pension
        equity_value = (
            enterprise_value
            - net_debt
            - minority_interest
            - preferred_stock
            + deferred_tax_assets
            - pension_deficit
        )
        
        # Store equity bridge for transparency
        equity_bridge = {
            "net_debt": net_debt,
            "minority_interest": minority_interest,
            "preferred_stock": preferred_stock,
            "deferred_tax_assets": deferred_tax_assets,
            "pension_deficit": pension_deficit,
        }

        # Intrinsic value per share (prefer diluted shares for DCF)
        current_shares = extractor.shares_outstanding() or 1
        # Determine which shares figure was used for transparency
        shares_type = extractor.shares_outstanding_type()
        
        # Account for SBC dilution over projection period
        # Terminal shares = current shares * (1 + dilution_rate)^years
        terminal_shares = current_shares * ((1 + annual_dilution_rate) ** projection_years)
        
        # Use terminal shares for per-share value (accounts for future dilution)
        intrinsic_value_per_share = equity_value / terminal_shares

        # 6. Sensitivity Analysis
        sensitivity_calc = SensitivityCalculator(
            projected_fcfs=projected_fcf,
            projection_years=projection_years,
            shares_outstanding=terminal_shares,  # Use terminal shares for consistency
            total_debt=total_debt,
            cash=cash,
            # Pass equity bridge components for consistency
            minority_interest=minority_interest,
            preferred_stock=preferred_stock,
            deferred_tax_assets=deferred_tax_assets,
            pension_deficit=pension_deficit,
        )
        
        # Generate matrix with discount rate vs terminal growth
        # Discount rate: current ± 2% in 1% steps
        # Terminal growth: 1.5% to 4.5% in 0.5% steps
        sensitivity = sensitivity_calc.generate_matrix(
            base_discount_rate=discount_rate,
            base_terminal_growth=terminal_growth_rate,
            discount_rate_steps=[-0.02, -0.01, 0, 0.01, 0.02],
            terminal_growth_steps=[-0.015, -0.01, -0.005, 0, 0.005, 0.01, 0.015],
        )

        # 7. Calculate value drivers (what moves intrinsic value most)
        # Pass FCF projector and base ratios so we can perturb-and-revalue
        effective_revenue_growth = revenue_growth or fcf_projector.revenue_cagr()
        effective_operating_margin = operating_margin or fcf_projector.operating_margin()
        effective_da_ratio = da_ratio or fcf_projector.da_to_revenue_ratio()
        effective_capex_ratio = capex_ratio or fcf_projector.capex_to_revenue_ratio()
        effective_wc_ratio = wc_ratio or fcf_projector.wc_to_revenue_ratio()
        
        value_drivers = self._calculate_value_drivers(
            base_value=intrinsic_value_per_share,
            fcf_projector=fcf_projector,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            projection_years=projection_years,
            shares=terminal_shares,  # Use terminal shares for consistency
            net_debt=net_debt,
            revenue_growth=effective_revenue_growth,
            operating_margin=effective_operating_margin,
            da_ratio=effective_da_ratio,
            capex_ratio=effective_capex_ratio,
            wc_ratio=effective_wc_ratio,
            # Match main valuation methodology
            wc_mode=wc_mode,
            use_mid_year_discounting=use_mid_year_discounting,
            # Multi-stage schedules (if provided, match main valuation)
            growth_schedule=growth_schedule,
            margin_schedule=margin_schedule,
            da_schedule=da_schedule,
            capex_schedule=capex_schedule,
            wc_schedule=wc_schedule,
            # Equity bridge for full calculation
            minority_interest=minority_interest,
            preferred_stock=preferred_stock,
            deferred_tax_assets=deferred_tax_assets,
            pension_deficit=pension_deficit,
        )

        # 8. Terminal Value sanity check via Exit Multiple AND dominance warning
        # Professional valuation cross-checks Gordon Growth with implied EV/EBITDA
        # Also warns if terminal value dominates (>70% of EV)
        # P0 Fix: Also checks implied terminal ROIC vs WACC for economic sanity
        terminal_value_check = self._calculate_terminal_value_check(
            terminal_value=terminal_value,
            terminal_year_projection=projections[-1],
            pv_terminal=pv_terminal,
            enterprise_value=enterprise_value,
            sector_ev_ebitda_multiple=sector_ev_ebitda_multiple,
            terminal_growth_rate=terminal_growth_rate,
            wacc=discount_rate,
        )

        # 9. Capital Efficiency - ROIC, Value Spread, Economic Profit
        # NOTES4: Add capital efficiency metrics to main valuation response
        # IMPORTANT: Use calculated_wacc (true cost of capital), not discount_rate
        # (which may be a user override). Value creation should be measured against
        # the actual WACC, not an arbitrary discount rate.
        capital_efficiency = self._calculate_capital_efficiency(
            extractor=extractor,
            wacc=calculated_wacc if calculated_wacc is not None else discount_rate,
            revenue_growth=effective_revenue_growth,
        )

        return {
            "symbol": symbol,
            "data_provider": stock_data.provider,
            "data_fetched_at": data_fetched_at,
            "intrinsic_value_per_share": intrinsic_value_per_share,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "market_cap": extractor.market_cap(),
            "net_debt": net_debt,
            "equity_bridge": equity_bridge,
            "wacc": calculated_wacc,
            "discount_rate": discount_rate,
            "using_custom_discount_rate": discount_rate_override is not None,
            "terminal_value": terminal_value,
            "projections": projections,
            "inputs": {
                "risk_free_rate": risk_free_rate,
                "beta": extractor.beta(),
                "market_risk_premium": extractor.market_risk_premium(),
                "cost_of_debt": extractor.cost_of_debt(risk_free_rate=risk_free_rate),
                "tax_rate": extractor.tax_rate(),
                "revenue_growth": revenue_growth or fcf_projector.revenue_cagr(),
                "operating_margin": operating_margin or fcf_projector.operating_margin(),
                "terminal_growth_rate": terminal_growth_rate,
                "projection_years": projection_years,
                "discount_rate_override": discount_rate_override,
                "shares_outstanding": current_shares,
                "shares_type": shares_type,  # "diluted" (preferred) or "basic" (fallback)
                "annual_dilution_rate": annual_dilution_rate,
                "terminal_shares": terminal_shares,  # Shares at end of projection period
            },
            "sensitivity": sensitivity,
            "value_drivers": value_drivers,
            "terminal_value_check": terminal_value_check,
            "business_type_warning": business_type_warning,
            "capital_efficiency": capital_efficiency,
        }
    
    def _calculate_value_drivers(
        self,
        base_value: float,
        fcf_projector: FCFProjector,
        discount_rate: float,
        terminal_growth_rate: float,
        projection_years: int,
        shares: float,
        net_debt: float,
        revenue_growth: float,
        operating_margin: float,
        da_ratio: float,
        capex_ratio: float,
        wc_ratio: float,
        wc_mode: str = "level",
        use_mid_year_discounting: bool = False,
        # Multi-stage schedules (if provided, used instead of constant values)
        growth_schedule: Optional[List[float]] = None,
        margin_schedule: Optional[List[float]] = None,
        da_schedule: Optional[List[float]] = None,
        capex_schedule: Optional[List[float]] = None,
        wc_schedule: Optional[List[float]] = None,
        # Equity bridge
        minority_interest: float = 0.0,
        preferred_stock: float = 0.0,
        deferred_tax_assets: float = 0.0,
        pension_deficit: float = 0.0,
    ) -> List[Dict]:
        """
        Calculate which inputs have the largest impact on intrinsic value.
        
        Uses perturb-and-revalue: actually re-runs the DCF with ±10% changes
        to each input and measures the resulting change in intrinsic value.
        
        This is superior to proxy methods because it captures the full
        non-linear interactions in the DCF model.
        
        IMPORTANT: Uses the same methodology as the main valuation:
        - wc_mode (level vs incremental)
        - use_mid_year_discounting
        - Multi-stage schedules (growth, margin, da, capex, wc)
        """
        drivers = []
        
        # Discount offset for mid-year discounting (same as main valuation)
        discount_offset = 0.5 if use_mid_year_discounting else 0.0
        
        # Helper to run full DCF and get intrinsic value
        def calc_full_value(
            growth: float = revenue_growth,
            margin: float = operating_margin,
            dr: float = discount_rate,
            tg: float = terminal_growth_rate,
            # Allow perturbing schedules directly (for multi-stage sensitivity)
            perturbed_growth_schedule: Optional[List[float]] = None,
            perturbed_margin_schedule: Optional[List[float]] = None,
        ) -> Optional[float]:
            if dr <= tg:
                return None
            
            # Re-project FCF with new inputs
            # Use perturbed schedules if provided, otherwise use base schedules
            projections = fcf_projector.project(
                years=projection_years,
                revenue_growth=growth,
                operating_margin=margin,
                da_ratio=da_ratio,
                capex_ratio=capex_ratio,
                wc_ratio=wc_ratio,
                wc_mode=wc_mode,
                # Use perturbed schedules for sensitivity, or base schedules
                growth_schedule=perturbed_growth_schedule or growth_schedule,
                margin_schedule=perturbed_margin_schedule or margin_schedule,
                da_schedule=da_schedule,
                capex_schedule=capex_schedule,
                wc_schedule=wc_schedule,
            )
            
            projected_fcf = [p["fcf"] for p in projections]
            
            # Calculate DCF value (using same discounting as main valuation)
            pv_fcf = sum(
                fcf / ((1 + dr) ** (year - discount_offset))
                for year, fcf in enumerate(projected_fcf, start=1)
            )
            
            final_fcf = projected_fcf[-1]
            terminal_value = final_fcf * (1 + tg) / (dr - tg)
            pv_terminal = terminal_value / ((1 + dr) ** (projection_years - discount_offset))
            
            enterprise_value = pv_fcf + pv_terminal
            
            # Full equity bridge
            equity_value = (
                enterprise_value
                - net_debt
                - minority_interest
                - preferred_stock
                + deferred_tax_assets
                - pension_deficit
            )
            
            return equity_value / shares if shares > 0 else None
        
        # Test discount rate sensitivity (+/- 1 percentage point)
        val_high_dr = calc_full_value(dr=discount_rate + 0.01)
        val_low_dr = calc_full_value(dr=discount_rate - 0.01)
        if val_high_dr and val_low_dr and base_value:
            dr_impact = abs(val_high_dr - val_low_dr) / base_value * 100
            drivers.append({
                "input": "discount_rate",
                "impact_percent": round(dr_impact, 1),
                "description": "±1% change in discount rate",
            })
        
        # Test terminal growth sensitivity (+/- 0.5 percentage point)
        val_high_tg = calc_full_value(tg=terminal_growth_rate + 0.005)
        val_low_tg = calc_full_value(tg=terminal_growth_rate - 0.005)
        if val_high_tg and val_low_tg and base_value:
            tg_impact = abs(val_high_tg - val_low_tg) / base_value * 100
            drivers.append({
                "input": "terminal_growth",
                "impact_percent": round(tg_impact, 1),
                "description": "±0.5% change in terminal growth",
            })
        
        # Test revenue growth sensitivity (+/- 10% relative change)
        # E.g., 8% growth becomes 7.2% (-10%) and 8.8% (+10%)
        # IMPORTANT: If growth_schedule exists, we must perturb the schedule itself,
        # not just the single value (which would be ignored by project())
        if growth_schedule:
            # Perturb entire schedule by ±10%
            high_growth_schedule = [g * 1.10 for g in growth_schedule]
            low_growth_schedule = [g * 0.90 for g in growth_schedule]
            val_high_growth = calc_full_value(perturbed_growth_schedule=high_growth_schedule)
            val_low_growth = calc_full_value(perturbed_growth_schedule=low_growth_schedule)
            avg_growth = sum(growth_schedule) / len(growth_schedule)
            growth_desc = f"±10% change in growth schedule (avg {avg_growth*100:.1f}%)"
        else:
            growth_delta = revenue_growth * 0.10  # 10% of current growth
            if growth_delta > 0.001:  # Only test if growth is meaningful
                val_high_growth = calc_full_value(growth=revenue_growth + growth_delta)
                val_low_growth = calc_full_value(growth=revenue_growth - growth_delta)
            else:
                val_high_growth = val_low_growth = None
            growth_desc = f"±10% change in revenue growth ({revenue_growth*100:.1f}% base)"
        
        if val_high_growth and val_low_growth and base_value:
            growth_impact = abs(val_high_growth - val_low_growth) / base_value * 100
            drivers.append({
                "input": "revenue_growth",
                "impact_percent": round(growth_impact, 1),
                "description": growth_desc,
            })
        
        # Test operating margin sensitivity (+/- 10% relative change)
        # E.g., 25% margin becomes 22.5% (-10%) and 27.5% (+10%)
        # IMPORTANT: If margin_schedule exists, we must perturb the schedule itself
        if margin_schedule:
            # Perturb entire schedule by ±10%
            high_margin_schedule = [m * 1.10 for m in margin_schedule]
            low_margin_schedule = [m * 0.90 for m in margin_schedule]
            val_high_margin = calc_full_value(perturbed_margin_schedule=high_margin_schedule)
            val_low_margin = calc_full_value(perturbed_margin_schedule=low_margin_schedule)
            avg_margin = sum(margin_schedule) / len(margin_schedule)
            margin_desc = f"±10% change in margin schedule (avg {avg_margin*100:.1f}%)"
        else:
            margin_delta = operating_margin * 0.10  # 10% of current margin
            if margin_delta > 0.001:  # Only test if margin is meaningful
                val_high_margin = calc_full_value(margin=operating_margin + margin_delta)
                val_low_margin = calc_full_value(margin=operating_margin - margin_delta)
            else:
                val_high_margin = val_low_margin = None
            margin_desc = f"±10% change in operating margin ({operating_margin*100:.1f}% base)"
        
        if val_high_margin and val_low_margin and base_value:
            margin_impact = abs(val_high_margin - val_low_margin) / base_value * 100
            drivers.append({
                "input": "operating_margin",
                "impact_percent": round(margin_impact, 1),
                "description": margin_desc,
            })
        
        # Sort by impact (highest first)
        drivers.sort(key=lambda x: x["impact_percent"], reverse=True)
        
        return drivers
    
    def _calculate_terminal_value_check(
        self,
        terminal_value: float,
        terminal_year_projection: Dict,
        pv_terminal: float,
        enterprise_value: float,
        sector_ev_ebitda_multiple: Optional[float] = None,
        terminal_growth_rate: float = 0.03,
        wacc: Optional[float] = None,
    ) -> Dict:
        """
        Calculate implied exit multiple and terminal dominance as sanity checks.
        
        Professional valuation cross-checks Gordon Growth Model terminal value
        with an implied EV/EBITDA exit multiple. If the implied multiple is
        unrealistically high (> 25x for mature companies), it suggests the
        terminal growth assumption may be too aggressive.
        
        Also cross-checks with Exit Multiple Method if sector multiple provided.
        If Gordon Growth TV and Exit Multiple TV diverge by >20%, it indicates
        inconsistency between growth assumptions and market multiples.
        
        Also checks if terminal value dominates enterprise value (>70%),
        indicating the DCF is essentially a terminal value guess.
        
        P0 Fix: Also calculates implied terminal ROIC and warns if >> WACC.
        In perpetuity, growth requires reinvestment: g = Reinvestment Rate × ROIC.
        Implied ROIC = g / (1 - FCF/NOPAT). If implied ROIC >> WACC, the model
        assumes "infinite competitive advantage" which is economically heroic.
        
        Returns dict with:
        - terminal_ebitda: EBIT + D&A in terminal year
        - implied_exit_multiple: Terminal Value / Terminal EBITDA
        - terminal_value_pct: PV(Terminal) / Enterprise Value
        - gordon_growth_tv: Terminal value via Gordon Growth (for transparency)
        - exit_multiple_tv: Terminal value via Exit Multiple (if sector multiple provided)
        - method_divergence_pct: Divergence between methods (if both available)
        - implied_terminal_roic: Implied ROIC in perpetuity
        - warning: Optional warning if multiple seems unrealistic
        - dominance_warning: Optional warning if TV dominates EV
        - method_divergence_warning: Optional warning if methods diverge >20%
        - terminal_roic_warning: Optional warning if implied ROIC >> WACC
        """
        # Terminal year EBITDA = EBIT + D&A
        terminal_ebit = terminal_year_projection.get("ebit", 0)
        terminal_da = terminal_year_projection.get("da", 0)
        terminal_ebitda = terminal_ebit + terminal_da
        
        # Calculate terminal value % of EV
        terminal_value_pct = pv_terminal / enterprise_value if enterprise_value > 0 else 0
        
        # Avoid division by zero for exit multiple
        if terminal_ebitda <= 0:
            return {
                "terminal_ebitda": terminal_ebitda,
                "implied_exit_multiple": None,
                "terminal_value_pct": terminal_value_pct,
                "gordon_growth_tv": terminal_value,
                "implied_terminal_roic": None,  # P0 Fix: Always include this field
                "warning": "Cannot calculate exit multiple - terminal EBITDA is zero or negative",
            }
        
        # Implied EV/EBITDA = Terminal Value / Terminal Year EBITDA
        implied_multiple = terminal_value / terminal_ebitda
        
        result = {
            "terminal_ebitda": terminal_ebitda,
            "implied_exit_multiple": implied_multiple,
            "terminal_value_pct": terminal_value_pct,
            "gordon_growth_tv": terminal_value,
        }
        
        # Exit Multiple Method cross-check (if sector multiple provided)
        if sector_ev_ebitda_multiple is not None and sector_ev_ebitda_multiple > 0:
            exit_multiple_tv = terminal_ebitda * sector_ev_ebitda_multiple
            result["exit_multiple_tv"] = exit_multiple_tv
            result["sector_ev_ebitda_multiple"] = sector_ev_ebitda_multiple
            
            # Calculate divergence: (Gordon - Exit Multiple) / Exit Multiple
            divergence_pct = (terminal_value - exit_multiple_tv) / exit_multiple_tv
            result["method_divergence_pct"] = divergence_pct
            
            # Warn if methods diverge by more than 20%
            if abs(divergence_pct) > 0.20:
                if divergence_pct > 0:
                    direction = "higher"
                    explanation = (
                        "This suggests terminal growth assumption may be too aggressive, "
                        "or the sector multiple is too conservative for this company's profile."
                    )
                else:
                    direction = "lower"
                    explanation = (
                        "This suggests terminal growth assumption may be too conservative, "
                        "or the sector multiple is too optimistic for this company's profile."
                    )
                
                result["method_divergence_warning"] = (
                    f"Gordon Growth terminal value (${terminal_value/1e9:.1f}B) is "
                    f"{abs(divergence_pct):.0%} {direction} than Exit Multiple method "
                    f"(${exit_multiple_tv/1e9:.1f}B at {sector_ev_ebitda_multiple:.1f}x). "
                    f"{explanation}"
                )
        
        # Add warning if multiple is unrealistically high
        # For mature companies, EV/EBITDA > 25x is aggressive
        # For high-growth tech, up to 30-40x might be justified
        if implied_multiple > 25:
            result["warning"] = (
                f"Implied exit multiple ({implied_multiple:.1f}x EV/EBITDA) is high. "
                "Consider whether terminal growth assumption is too aggressive, "
                "or if the company's growth profile justifies this premium."
            )
        
        # Add dominance warning if terminal value is >70% of EV
        if terminal_value_pct > 0.70:
            result["dominance_warning"] = (
                f"Terminal value represents {terminal_value_pct:.0%} of enterprise value. "
                "When >70%, the DCF is essentially a terminal value guess. Consider: "
                "(1) extending projection period until steady state, "
                "(2) using revenue/EBITDA multiples instead, or "
                "(3) validating terminal assumptions carefully."
            )
        
        # P1 Fix: CapEx/D&A convergence check
        # In terminal (steady-state), Growth CapEx should be ~0 and Maintenance CapEx ≈ D&A
        # If CapEx >> D&A, the model implies perpetual growth investment, which is inconsistent
        terminal_capex = terminal_year_projection.get("capex", 0)
        if terminal_da > 0:
            capex_da_ratio = terminal_capex / terminal_da
            result["terminal_capex_to_da"] = capex_da_ratio
            
            # Warn if CapEx/D&A > 1.3x (30% above maintenance)
            if capex_da_ratio > 1.3:
                result["capex_convergence_warning"] = (
                    f"Terminal CapEx ({capex_da_ratio:.2f}x D&A) exceeds maintenance level. "
                    "In perpetuity, CapEx should converge to D&A (1.0x) as Growth CapEx → 0. "
                    f"Current assumption implies {(capex_da_ratio - 1):.0%} perpetual growth investment. "
                    "Consider reducing terminal CapEx/Revenue ratio, or using multi-stage "
                    "with declining CapEx intensity in the mature phase."
                )
        
        # P0 Fix: Calculate implied terminal ROIC and warn if >> WACC
        # In perpetuity: g = Reinvestment Rate × ROIC
        # Reinvestment Rate = 1 - (FCF / NOPAT)
        # Therefore: Implied ROIC = g / (1 - FCF/NOPAT)
        terminal_nopat = terminal_year_projection.get("nopat", 0)
        terminal_fcf = terminal_year_projection.get("fcf", 0)
        
        implied_roic = None
        if terminal_nopat > 0 and terminal_growth_rate > 0:
            # FCF/NOPAT ratio - if FCF >= NOPAT, no reinvestment needed (unrealistic in perpetuity)
            fcf_nopat_ratio = terminal_fcf / terminal_nopat
            reinvestment_rate = 1 - fcf_nopat_ratio
            
            if reinvestment_rate > 0.01:  # Need at least some reinvestment
                implied_roic = terminal_growth_rate / reinvestment_rate
                result["implied_terminal_roic"] = implied_roic
                
                # Warn if implied ROIC >> WACC (more than 2x)
                # This indicates "economically heroic" assumptions
                if wacc is not None and implied_roic > wacc * 2:
                    result["terminal_roic_warning"] = (
                        f"Implied terminal ROIC ({implied_roic:.0%}) is {implied_roic/wacc:.1f}x WACC ({wacc:.0%}). "
                        "In a competitive economy, ROIC should fade toward WACC in perpetuity. "
                        "This assumption implies an 'infinite competitive advantage'. Consider: "
                        "(1) reducing terminal growth rate, "
                        "(2) increasing terminal reinvestment (lower FCF/NOPAT ratio), or "
                        "(3) validating the company's sustainable competitive moat."
                    )
            else:
                # Reinvestment rate near zero implies infinite ROIC (unsustainable)
                result["implied_terminal_roic"] = None
                if wacc is not None:
                    result["terminal_roic_warning"] = (
                        "Terminal FCF equals or exceeds NOPAT (no reinvestment). "
                        "With positive terminal growth, this implies infinite ROIC - "
                        "perpetual growth without capital investment. This is economically impossible."
                    )
        elif terminal_growth_rate > 0:
            # Terminal NOPAT <= 0 but positive growth - economically inconsistent
            result["implied_terminal_roic"] = None
        else:
            # No terminal growth (g=0) - ROIC calculation not applicable
            result["implied_terminal_roic"] = None
        
        return result
    
    def _get_business_type_warning(
        self,
        sector: Optional[str],
        industry: Optional[str],
    ) -> Optional[str]:
        """
        P2.8: Generate a warning for financial companies where DCF is less appropriate.
        
        Banks, insurers, and other financial services companies have fundamentally
        different business models where:
        - The balance sheet IS the product (banks lend deposits, insurers invest float)
        - Interest income is revenue, not a financing cost
        - Working capital and CapEx concepts don't apply traditionally
        - Book value and P/B ratio are the primary metrics
        
        Returns:
            Warning message if financial company, None otherwise
        """
        if not sector and not industry:
            return None
        
        # Normalize industry name (hyphen vs em-dash variants)
        normalized_industry = industry.replace("-", "—") if industry else ""
        
        # Check if this is a financial company
        is_financial_sector = sector in self.FINANCIAL_SECTORS if sector else False
        is_financial_industry = (
            industry in self.FINANCIAL_INDUSTRIES or
            normalized_industry in self.FINANCIAL_INDUSTRIES
        ) if industry else False
        
        if not (is_financial_sector or is_financial_industry):
            return None
        
        # Build descriptive warning
        classification = []
        if sector:
            classification.append(f"Sector: {sector}")
        if industry:
            classification.append(f"Industry: {industry}")
        classification_str = " | ".join(classification)
        
        return (
            f"⚠️ Financial Company Detected ({classification_str}). "
            "Traditional DCF may be less appropriate for banks, insurers, and other "
            "financial services companies because: "
            "(1) The balance sheet IS the business — banks lend deposits, insurers invest float. "
            "(2) Interest income is operating revenue, not a financing cost, so EBIT and FCF are distorted. "
            "(3) Working capital and CapEx concepts don't apply in the traditional sense. "
            "Consider using: "
            "• Price/Book (P/B) ratio as the primary valuation metric, "
            "• Dividend Discount Model (DDM) for stable dividend payers, "
            "• Excess Returns / Residual Income Model for banks."
        )
    
    def _calculate_capital_efficiency(
        self,
        extractor: DataExtractor,
        wacc: float,
        revenue_growth: float,
    ) -> dict:
        """
        Calculate capital efficiency metrics for NOTES4 integration.
        
        ROIC (Return on Invested Capital) = NOPAT / Invested Capital
        Value Spread = ROIC - WACC (positive = value creation)
        Economic Profit = Value Spread × Invested Capital
        
        Args:
            extractor: DataExtractor instance with financial data
            wacc: Weighted Average Cost of Capital (used as discount rate)
            revenue_growth: Expected revenue growth rate
            
        Returns:
            Dictionary with:
            - roic: Return on Invested Capital
            - value_spread: ROIC - WACC
            - economic_profit: Dollar value created/destroyed
            - is_value_creating: Boolean (ROIC > WACC)
            - invested_capital: Total invested capital
            - nopat: Net Operating Profit After Tax
        """
        # Get operating income (EBIT) and tax rate
        operating_income = extractor.latest_operating_income()
        tax_rate = extractor.tax_rate() or 0.25  # Default to 25% if unavailable
        
        # Calculate NOPAT = EBIT × (1 - Tax Rate)
        nopat = None
        if operating_income is not None:
            nopat = operating_income * (1 - tax_rate)
        
        # Calculate Invested Capital = Equity + Debt - Excess Cash
        total_equity = extractor.total_equity()
        total_debt = extractor.total_debt() or 0
        cash = extractor.cash() or 0
        revenue = extractor.latest_revenue() or 0
        
        # Excess cash = Total Cash - Operating Cash (estimated at 2% of revenue)
        operating_cash = revenue * 0.02 if revenue > 0 else 0
        excess_cash = max(0, cash - operating_cash)
        
        invested_capital = None
        if total_equity is not None:
            invested_capital = total_equity + total_debt - excess_cash
        
        # Return early if missing data
        if nopat is None or invested_capital is None or invested_capital <= 0:
            return {
                "roic": None,
                "value_spread": None,
                "economic_profit": None,
                "is_value_creating": None,
                "invested_capital": invested_capital,
                "nopat": nopat,
                "data_issue": "Missing operating income or invested capital data",
            }
        
        # Use the capital efficiency module for calculations
        result = analyze_value_creation(
            nopat=nopat,
            invested_capital=invested_capital,
            revenue_growth=revenue_growth,
            wacc=wacc,
        )
        
        # Add invested_capital and nopat for consistent schema with error case
        result["invested_capital"] = invested_capital
        result["nopat"] = nopat
        
        return result

