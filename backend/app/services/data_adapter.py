"""
Adapter to convert standardized StockData to the legacy dict format
expected by DataExtractor and other services.
"""
from app.services.base_provider import StockData


def stock_data_to_legacy(stock_data: StockData) -> dict:
    """
    Convert standardized StockData to the legacy FMP dict format
    that DataExtractor and other services expect.
    """
    profile = stock_data.profile
    financials = stock_data.financials
    
    # Build profile dict
    profile_dict = {
        "symbol": profile.symbol,
        "companyName": profile.name,
        "price": profile.price,
        "marketCap": profile.market_cap,
        "beta": profile.beta,
        "sharesOutstanding": profile.shares_outstanding,
        "currency": profile.currency,
        "exchange": profile.exchange,
        "industry": profile.industry,
        "sector": profile.sector,
    }
    
    # Build financial statement lists
    income_statements = []
    balance_sheets = []
    cash_flows = []
    
    for fin in financials:
        # Normalize period for all statement types (TTM, FY, or Q)
        period = "TTM" if fin.period in ("ttm", "TTM") else ("FY" if fin.period == "annual" else "Q")
        
        # Income statement
        income_statements.append({
            "date": fin.date,
            "period": period,
            "revenue": fin.revenue,
            "costOfRevenue": fin.cost_of_revenue,
            "grossProfit": fin.gross_profit,
            "operatingIncome": fin.operating_income,
            "netIncome": fin.net_income,
            "interestExpense": fin.interest_expense,
            "incomeTaxExpense": fin.income_tax_expense,
            "sellingGeneralAndAdministrative": fin.selling_general_admin,
            # Calculate incomeBeforeTax for tax rate calculation
            "incomeBeforeTax": (fin.net_income + fin.income_tax_expense) 
                if fin.net_income is not None and fin.income_tax_expense is not None 
                else None,
            # Share counts - prefer financial statement data, fallback to profile
            "weightedAverageShsOut": fin.weighted_avg_shares or profile.shares_outstanding,
            "weightedAverageShsOutDil": fin.weighted_avg_shares_diluted,
        })
        
        # Balance sheet
        balance_sheets.append({
            "date": fin.date,
            "period": period,  # CRITICAL: Must match income_statement for annual filtering
            "totalAssets": fin.total_assets,
            "totalLiabilities": fin.total_liabilities,
            "totalStockholdersEquity": fin.total_equity,
            "totalDebt": fin.total_debt,
            "cashAndCashEquivalents": fin.cash_and_equivalents,
            "totalCurrentAssets": fin.current_assets,
            "totalCurrentLiabilities": fin.current_liabilities,
            "shortTermDebt": fin.short_term_debt,
            "goodwill": fin.goodwill,
            "intangibleAssets": fin.intangible_assets,
            "retainedEarnings": fin.retained_earnings,
            "netReceivables": fin.net_receivables,
            "propertyPlantEquipmentNet": fin.property_plant_equipment,
            # Equity Bridge components
            "minorityInterest": fin.minority_interest,
            "preferredStock": fin.preferred_stock,
            "deferredTaxAssets": fin.deferred_tax_assets,
            "pensionLiability": fin.pension_liability,
        })
        
        # Cash flow
        cash_flows.append({
            "date": fin.date,
            "period": period,  # CRITICAL: Must match income_statement for annual filtering
            "operatingCashFlow": fin.operating_cash_flow,
            "capitalExpenditure": fin.capital_expenditure,
            "freeCashFlow": fin.free_cash_flow,
            "depreciationAndAmortization": fin.depreciation_amortization,
            "dividendsPaid": fin.dividends_paid,
            "stockBasedCompensation": fin.stock_based_compensation,
        })
    
    return {
        "profile": profile_dict,
        "income_statement": income_statements,
        "balance_sheet": balance_sheets,
        "cash_flow": cash_flows,
    }


