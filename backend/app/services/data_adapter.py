"""
Adapter to convert standardized StockData to the legacy dict format
expected by DataExtractor and other services.
"""
from typing import Dict, Any
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
            "grossProfitRatio": fin.gross_profit_ratio or ((fin.gross_profit / fin.revenue) if fin.gross_profit is not None and fin.revenue and fin.revenue != 0 else None),
            "operatingIncome": fin.operating_income,
            "netIncome": fin.net_income,
            "interestExpense": fin.interest_expense,
            "incomeTaxExpense": fin.income_tax_expense,
            "sellingGeneralAndAdministrative": fin.selling_general_admin,
            "researchAndDevelopment": fin.research_development,
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
            "inventory": fin.inventory,
            "accountPayables": fin.accounts_payable,
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
            "shareRepurchases": fin.share_repurchases,  # For Total Shareholder Yield
        })
    
    return {
        "profile": profile_dict,
        "income_statement": income_statements,
        "balance_sheet": balance_sheets,
        "cash_flow": cash_flows,
    }


def ixbrl_facts_to_legacy(facts_by_date: Dict[str, Dict[str, Any]]) -> dict:
    """
    Convert extracted multi-period iXBRL facts into the legacy dict format.
    Sorted by date (latest first).
    """
    income_statements = []
    balance_sheets = []
    cash_flows = []
    
    # Sort dates latest first
    sorted_dates = sorted(facts_by_date.keys(), reverse=True)
    
    for date_str in sorted_dates:
        facts = facts_by_date[date_str]
        
        income_statements.append({
            "date": date_str,
            "period": "FY",
            "revenue": facts.get("revenue"),
            "netIncome": facts.get("net_income"),
            "grossProfit": facts.get("gross_profit"),
            "grossProfitRatio": (facts.get("gross_profit") / facts.get("revenue")) if facts.get("gross_profit") is not None and facts.get("revenue") else None,
            "operatingIncome": facts.get("ebit") or facts.get("operating_income"),
            "costOfRevenue": facts.get("cost_of_revenue"),
            "interestExpense": facts.get("interest_expense"),
            "incomeTaxExpense": facts.get("tax_expense"),
            "incomeBeforeTax": facts.get("ebt"),
            "researchAndDevelopment": facts.get("research_and_development"), # Added mapping for R&D
            "weightedAverageShsOut": facts.get("shares"),
            "weightedAverageShsOutDil": facts.get("shares_diluted"),
        })
        
        balance_sheets.append({
            "date": date_str,
            "period": "FY",
            "totalAssets": facts.get("total_assets"),
            "totalLiabilities": facts.get("total_liabilities"),
            "totalStockholdersEquity": facts.get("equity"),
            "totalDebt": facts.get("total_debt") or ((facts.get("short_term_debt") or 0) + (facts.get("long_term_debt") or 0)),
            "totalCurrentAssets": facts.get("current_assets"),
            "totalCurrentLiabilities": facts.get("current_liabilities"),
            "shortTermDebt": facts.get("short_term_debt"),
            "longTermDebt": facts.get("long_term_debt"),
            "inventory": facts.get("inventory"),
            "netReceivables": facts.get("accounts_receivable"),
            "retainedEarnings": facts.get("retained_earnings"),
            "propertyPlantEquipmentNet": facts.get("ppe_net"),
            "cashAndCashEquivalents": facts.get("cash"),
            "goodwill": facts.get("goodwill"),
            "intangibleAssets": facts.get("intangibles"),
            "accountPayables": facts.get("accounts_payable"),
        })
        
        cash_flows.append({
            "date": date_str,
            "period": "FY",
            "operatingCashFlow": facts.get("operating_cash_flow"),
            "capitalExpenditure": facts.get("capex"),
            "depreciationAndAmortization": facts.get("da"),
            "stockBasedCompensation": facts.get("sbc"),
            "dividendsPaid": facts.get("dividends"),
        })
    
    return {
        "profile": {"marketCap": 0, "symbol": "Filing"},
        "income_statement": income_statements,
        "balance_sheet": balance_sheets,
        "cash_flow": cash_flows,
    }

