from typing import Optional
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
        # 1. Fetch data (with automatic provider fallback)
        stock_data = await self.client.get_stock_data(symbol)
        risk_free_rate = await self.client.get_treasury_rate()

        # 2. Convert to legacy format and extract inputs
        data = stock_data_to_legacy(stock_data)
        extractor = DataExtractor(data, market_risk_premium=market_risk_premium)

        # 3. Calculate WACC (only if all required components are available)
        beta = extractor.beta()
        cost_of_debt = extractor.cost_of_debt()
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
                tax_rate=tax_rate if tax_rate is not None else 0.25,
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
        )

        # 5. Run DCF
        projected_fcf = [p["fcf"] for p in projections]
        
        # Use the projected FCFs directly instead of growth-based projection
        # Calculate PV of projected FCFs
        pv_fcf = sum(
            fcf / ((1 + discount_rate) ** year)
            for year, fcf in enumerate(projected_fcf, start=1)
        )

        # Terminal value
        final_fcf = projected_fcf[-1]
        terminal_value = final_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)

        enterprise_value = pv_fcf + pv_terminal

        # Net debt adjustment
        total_debt = extractor.total_debt() or 0
        cash = extractor.cash() or 0
        net_debt = total_debt - cash
        equity_value = enterprise_value - net_debt

        # Intrinsic value per share
        shares = extractor.shares_outstanding() or 1
        intrinsic_value_per_share = equity_value / shares

        # 6. Sensitivity Analysis
        sensitivity_calc = SensitivityCalculator(
            projected_fcfs=projected_fcf,
            projection_years=projection_years,
            shares_outstanding=shares,
            total_debt=total_debt,
            cash=cash,
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

        return {
            "symbol": symbol,
            "data_provider": stock_data.provider,
            "intrinsic_value_per_share": intrinsic_value_per_share,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "market_cap": extractor.market_cap(),
            "net_debt": net_debt,
            "wacc": calculated_wacc,
            "discount_rate": discount_rate,
            "using_custom_discount_rate": discount_rate_override is not None,
            "terminal_value": terminal_value,
            "projections": projections,
            "inputs": {
                "risk_free_rate": risk_free_rate,
                "beta": extractor.beta(),
                "market_risk_premium": extractor.market_risk_premium(),
                "cost_of_debt": extractor.cost_of_debt(),
                "tax_rate": extractor.tax_rate(),
                "revenue_growth": revenue_growth or fcf_projector.revenue_cagr(),
                "operating_margin": operating_margin or fcf_projector.operating_margin(),
                "terminal_growth_rate": terminal_growth_rate,
                "projection_years": projection_years,
                "discount_rate_override": discount_rate_override,
            },
            "sensitivity": sensitivity,
        }

