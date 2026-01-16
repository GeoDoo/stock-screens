"""
Adapter to convert standardized StockData to the legacy dict format
expected by DataExtractor and other services.
"""
from typing import Dict, Any, List
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
            "investments": fin.investments,
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


def ixbrl_facts_to_legacy(facts_list: List[Dict[str, Any]]) -> dict:
    """
    Convert extracted multi-period iXBRL facts into the legacy dict format.
    Sorted by date (latest first).
    """
    income_statements = []
    balance_sheets = []
    cash_flows = []
    
    # Sort by date (latest first), then by duration (longer first for same date)
    sorted_facts = sorted(
        facts_list, 
        key=lambda x: (x.get("date", ""), x.get("duration", 0) or 0), 
        reverse=True
    )
    
    latest_shares = None
    if sorted_facts:
        # Find latest shares (usually point-in-time duration=0)
        share_facts = [f for f in sorted_facts if f.get("shares") is not None]
        if share_facts:
            latest_shares = share_facts[0].get("shares")

    for facts in sorted_facts:
        date_str = facts.get("date")
        duration = facts.get("duration")
        is_ltm = facts.get("is_ltm", False)
        
        # Determine period label
        if is_ltm:
            period = "TTM"
        elif duration == 0 or duration is None:
            period = "BS" # Balance Sheet / Instant
        elif 350 <= duration <= 375:
            period = "FY" # Full Year
        elif 80 <= duration <= 100:
            period = "Q"  # Quarter
        elif 170 <= duration <= 195:
            period = "6M"
        elif 260 <= duration <= 280:
            period = "9M"
        else:
            period = f"{duration}D" # Custom duration in days
            
        # Robust reconstruction of Total Liabilities and Total Debt
        # We must avoid overwriting explicit 0 values with fallback sums
        total_liabilities = facts.get("total_liabilities")
        if total_liabilities is None:
            cl = facts.get("current_liabilities")
            ncl = facts.get("noncurrent_liabilities")
            if cl is not None or ncl is not None:
                total_liabilities = (cl or 0) + (ncl or 0)
        
        total_debt = facts.get("total_debt")
        if total_debt is None:
            std = facts.get("short_term_debt")
            ltd = facts.get("long_term_debt")
            if std is not None or ltd is not None:
                total_debt = (std or 0) + (ltd or 0)

        gross_profit = facts.get("gross_profit")
        revenue = facts.get("revenue")
        cost_of_revenue = facts.get("cost_of_revenue")
        
        # Fallback: calculate gross_profit from revenue - cost_of_revenue
        if gross_profit is None and revenue is not None and cost_of_revenue is not None:
            gross_profit = revenue - cost_of_revenue
        
        gross_profit_ratio = (gross_profit / revenue) if gross_profit is not None and revenue and revenue != 0 else None
        
        operating_income = facts.get("ebit")
        if operating_income is None:
            operating_income = facts.get("operating_income")

        # Point-in-time facts go to Balance Sheet
        if duration == 0 or duration is None:
            balance_sheets.append({
                "date": date_str,
                "period": period,
                "totalAssets": facts.get("total_assets"),
                "totalLiabilities": total_liabilities,
                "totalStockholdersEquity": facts.get("equity"),
                "totalDebt": total_debt,
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
                # Equity Bridge components
                "minorityInterest": facts.get("minority_interest"),
                "preferredStock": facts.get("preferred_stock"),
                "deferredTaxAssets": facts.get("deferred_tax_assets"),
                "pensionLiability": facts.get("pension_liability"),
                "investments": facts.get("investments"),
            })
        else:
            # Flow facts go to Income Statement and Cash Flow
            income_statements.append({
                "date": date_str,
                "period": period,
                "revenue": revenue,
                "netIncome": facts.get("net_income"),
                "grossProfit": gross_profit,
                "grossProfitRatio": gross_profit_ratio,
                "operatingIncome": operating_income,
                "costOfRevenue": facts.get("cost_of_revenue"),
                "interestExpense": facts.get("interest_expense"),
                "incomeTaxExpense": facts.get("tax_expense"),
                "incomeBeforeTax": facts.get("ebt"),
                "researchAndDevelopment": facts.get("research_and_development"),
                "weightedAverageShsOut": facts.get("shares"),
                "weightedAverageShsOutDil": facts.get("shares_diluted"),
            })
            
            operating_cf = facts.get("operating_cash_flow")
            capex = facts.get("capex")
            # Calculate FCF: OCF - |CapEx| (normalize sign per project rules)
            free_cash_flow = None
            if operating_cf is not None and capex is not None:
                # CapEx should be positive expenditure; some filings report it negative
                free_cash_flow = operating_cf - abs(capex)
            
            cash_flows.append({
                "date": date_str,
                "period": period,
                "operatingCashFlow": operating_cf,
                "capitalExpenditure": capex,
                "freeCashFlow": free_cash_flow,
                "depreciationAndAmortization": facts.get("da"),
                "stockBasedCompensation": facts.get("sbc"),
                "dividendsPaid": facts.get("dividends"),
            })
    
    return {
        "profile": {
            "marketCap": 0, 
            "symbol": "Filing",
            "sharesOutstanding": latest_shares
        },
        "income_statement": income_statements,
        "balance_sheet": balance_sheets,
        "cash_flow": cash_flows,
    }

