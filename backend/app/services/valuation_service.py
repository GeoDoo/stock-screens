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


class ValuationService:
    """
    Orchestrates the full DCF valuation:
    1. Fetch data from the specified provider
    2. Extract inputs using DataExtractor
    3. Calculate WACC
    4. Project FCF using FCFProjector
    5. Run DCF to get intrinsic value
    """

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
        # SBC dilution - annual share growth rate from stock-based compensation
        annual_dilution_rate: float = 0.0,
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
        value_drivers = self._calculate_value_drivers(
            base_value=intrinsic_value_per_share,
            projected_fcf=projected_fcf,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            projection_years=projection_years,
            shares=terminal_shares,  # Use terminal shares for consistency
            total_debt=total_debt,
            cash=cash,
            revenue_growth=revenue_growth or fcf_projector.revenue_cagr(),
            operating_margin=operating_margin or fcf_projector.operating_margin(),
        )

        # 8. Terminal Value sanity check via Exit Multiple AND dominance warning
        # Professional valuation cross-checks Gordon Growth with implied EV/EBITDA
        # Also warns if terminal value dominates (>70% of EV)
        terminal_value_check = self._calculate_terminal_value_check(
            terminal_value=terminal_value,
            terminal_year_projection=projections[-1],
            pv_terminal=pv_terminal,
            enterprise_value=enterprise_value,
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
        }
    
    def _calculate_value_drivers(
        self,
        base_value: float,
        projected_fcf: List[float],
        discount_rate: float,
        terminal_growth_rate: float,
        projection_years: int,
        shares: float,
        total_debt: float,
        cash: float,
        revenue_growth: float,
        operating_margin: float,
    ) -> List[Dict]:
        """
        Calculate which inputs have the largest impact on intrinsic value.
        
        Tests +/- 10% changes to each input and ranks by value impact.
        """
        drivers = []
        
        # Helper to recalculate intrinsic value with modified inputs
        def calc_value(dr: float, tg: float) -> Optional[float]:
            if dr <= tg:
                return None
            sensitivity_calc = SensitivityCalculator(
                projected_fcfs=projected_fcf,
                projection_years=projection_years,
                shares_outstanding=shares,
                total_debt=total_debt,
                cash=cash,
            )
            return sensitivity_calc.calculate_intrinsic_value(dr, tg)
        
        # Test discount rate sensitivity (+/- 1 percentage point)
        val_high_dr = calc_value(discount_rate + 0.01, terminal_growth_rate)
        val_low_dr = calc_value(discount_rate - 0.01, terminal_growth_rate)
        if val_high_dr and val_low_dr and base_value:
            dr_impact = abs(val_high_dr - val_low_dr) / base_value * 100
            drivers.append({
                "input": "discount_rate",
                "impact_percent": round(dr_impact, 1),
                "description": "±1% change in discount rate",
            })
        
        # Test terminal growth sensitivity (+/- 0.5 percentage point)
        val_high_tg = calc_value(discount_rate, terminal_growth_rate + 0.005)
        val_low_tg = calc_value(discount_rate, terminal_growth_rate - 0.005)
        if val_high_tg and val_low_tg and base_value:
            tg_impact = abs(val_high_tg - val_low_tg) / base_value * 100
            drivers.append({
                "input": "terminal_growth",
                "impact_percent": round(tg_impact, 1),
                "description": "±0.5% change in terminal growth",
            })
        
        # Revenue growth impact (via FCF impact)
        # Higher growth = higher FCF = higher value
        drivers.append({
            "input": "revenue_growth",
            "impact_percent": round(revenue_growth * 100, 1),  # Proxy: growth rate itself
            "description": "Revenue compounds over projection period",
        })
        
        # Operating margin impact
        drivers.append({
            "input": "operating_margin",
            "impact_percent": round(operating_margin * 100, 1),  # Proxy: margin itself
            "description": "Margin directly scales EBIT → NOPAT → FCF",
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
    ) -> Dict:
        """
        Calculate implied exit multiple and terminal dominance as sanity checks.
        
        Professional valuation cross-checks Gordon Growth Model terminal value
        with an implied EV/EBITDA exit multiple. If the implied multiple is
        unrealistically high (> 25x for mature companies), it suggests the
        terminal growth assumption may be too aggressive.
        
        Also checks if terminal value dominates enterprise value (>70%),
        indicating the DCF is essentially a terminal value guess.
        
        Returns dict with:
        - terminal_ebitda: EBIT + D&A in terminal year
        - implied_exit_multiple: Terminal Value / Terminal EBITDA
        - terminal_value_pct: PV(Terminal) / Enterprise Value
        - warning: Optional warning if multiple seems unrealistic
        - dominance_warning: Optional warning if TV dominates EV
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
                "warning": "Cannot calculate exit multiple - terminal EBITDA is zero or negative",
            }
        
        # Implied EV/EBITDA = Terminal Value / Terminal Year EBITDA
        implied_multiple = terminal_value / terminal_ebitda
        
        result = {
            "terminal_ebitda": terminal_ebitda,
            "implied_exit_multiple": implied_multiple,
            "terminal_value_pct": terminal_value_pct,
        }
        
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
        
        return result

