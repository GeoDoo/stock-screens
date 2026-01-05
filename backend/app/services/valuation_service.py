from typing import Optional
from app.services.fmp_client import FMPClient
from app.services.data_extractor import DataExtractor
from app.services.wacc_calculator import WACCCalculator
from app.services.fcf_projector import FCFProjector
from app.services.dcf_calculator import DCFCalculator


class ValuationService:
    """
    Orchestrates the full DCF valuation:
    1. Fetch data from FMP
    2. Extract inputs using DataExtractor
    3. Calculate WACC
    4. Project FCF using FCFProjector
    5. Run DCF to get intrinsic value
    """

    def __init__(self, api_key: str):
        self.fmp_client = FMPClient(api_key=api_key)

    async def value_stock(
        self,
        symbol: str,
        projection_years: int = 5,
        terminal_growth_rate: float = 0.03,
        revenue_growth: Optional[float] = None,
        operating_margin: Optional[float] = None,
        market_risk_premium: Optional[float] = None,
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
        
        Returns:
            Dict with intrinsic value, WACC, projections, and inputs used
        """
        # 1. Fetch data
        data = await self.fmp_client.get_stock_data(symbol)
        risk_free_rate = await self.fmp_client.get_treasury_rate()

        # 2. Extract inputs
        extractor = DataExtractor(data, market_risk_premium=market_risk_premium)

        # 3. Calculate WACC
        # Use explicit None checks - 0.0 is a valid value, don't fallback
        beta = extractor.beta()
        cost_of_debt = extractor.cost_of_debt()
        tax_rate = extractor.tax_rate()
        market_cap = extractor.market_cap()
        total_debt = extractor.total_debt()

        wacc_calculator = WACCCalculator(
            risk_free_rate=risk_free_rate,
            beta=beta if beta is not None else 1.0,
            market_risk_premium=extractor.market_risk_premium(),
            cost_of_debt=cost_of_debt if cost_of_debt is not None else 0.05,
            tax_rate=tax_rate if tax_rate is not None else 0.25,
            market_cap=market_cap if market_cap is not None else 0,
            total_debt=total_debt if total_debt is not None else 0,
        )
        wacc = wacc_calculator.calculate()

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
        )

        # 5. Run DCF
        projected_fcf = [p["fcf"] for p in projections]
        
        # Use the projected FCFs directly instead of growth-based projection
        # Calculate PV of projected FCFs
        pv_fcf = sum(
            fcf / ((1 + wacc) ** year)
            for year, fcf in enumerate(projected_fcf, start=1)
        )

        # Terminal value
        final_fcf = projected_fcf[-1]
        terminal_value = final_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
        pv_terminal = terminal_value / ((1 + wacc) ** projection_years)

        enterprise_value = pv_fcf + pv_terminal

        # Net debt adjustment
        total_debt = extractor.total_debt() or 0
        cash = extractor.cash() or 0
        net_debt = total_debt - cash
        equity_value = enterprise_value - net_debt

        # Intrinsic value per share
        shares = extractor.shares_outstanding() or 1
        intrinsic_value_per_share = equity_value / shares

        return {
            "symbol": symbol,
            "intrinsic_value_per_share": intrinsic_value_per_share,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "market_cap": extractor.market_cap(),
            "net_debt": net_debt,
            "wacc": wacc,
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
            },
        }

