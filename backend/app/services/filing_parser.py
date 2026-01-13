import re
import bs4
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from app.services.logging_config import logger

class FilingParser:
    """
    Parses SEC HTML filings to extract specific sections (Items) and numerical data.
    Uses a combination of BeautifulSoup and robust regex to handle
    the variability in EDGAR HTML documents, including iXBRL support.
    """
    
    # Standard 10-K sections of interest
    SECTIONS = {
        "Item 1": r"ITEM\s+1\.\s+BUSINESS",
        "Item 1A": r"ITEM\s+1A\.\s+RISK\s+FACTORS",
        "Item 3": r"ITEM\s+3\.\s+LEGAL\s+PROCEEDINGS",
        "Item 7": r"ITEM\s+7\.\s+MANAGEMENT(?:\'S|\u2019S)\s+DISCUSSION\s+AND\s+ANALYSIS",
        "Item 7A": r"ITEM\s+7A\.\s+QUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES\s+ABOUT\s+MARKET\s+RISK",
        "Item 8": r"ITEM\s+8\.\s+FINANCIAL\s+STATEMENTS",
        "Item 9A": r"ITEM\s+9A\.\s+CONTROLS\s+AND\s+PROCEDURES",
    }

    # Common US-GAAP taxonomy tags for core financial metrics
    XBRL_MAPPINGS = {
        "net_income": ["us-gaap:NetIncomeLoss", "us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic", "us-gaap:ProfitLoss"],
        "revenue": [
            "us-gaap:Revenues", 
            "us-gaap:SalesRevenueNet", 
            "us-gaap:TotalRevenuesAndOtherIncome",
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax"
        ],
        "operating_cash_flow": ["us-gaap:NetCashProvidedByUsedInOperatingActivities"],
        "capex": ["us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "us-gaap:CapitalExpenditures", "us-gaap:PaymentsToAcquireProductiveAssets"],
        "total_assets": ["us-gaap:Assets"],
        "total_liabilities": ["us-gaap:Liabilities", "us-gaap:LiabilitiesAndStockholdersEquity"],
        "current_assets": ["us-gaap:AssetsCurrent"],
        "current_liabilities": ["us-gaap:LiabilitiesCurrent"],
        "inventory": ["us-gaap:InventoryNet", "us-gaap:InventoryNetCurrent"],
        "accounts_receivable": ["us-gaap:AccountsReceivableNetCurrent", "us-gaap:ReceivablesNetCurrent"],
        "retained_earnings": ["us-gaap:RetainedEarningsAccumulatedDeficit"],
        "ppe_net": ["us-gaap:PropertyPlantAndEquipmentNet"],
        "goodwill": ["us-gaap:Goodwill"],
        "intangibles": ["us-gaap:IntangibleAssetsNetExcludingGoodwill"],
        "gross_profit": ["us-gaap:GrossProfit"],
        "operating_income": ["us-gaap:OperatingIncomeLoss"],
        "ebit": ["us-gaap:OperatingIncomeLoss"],
        "interest_expense": ["us-gaap:InterestExpense", "us-gaap:InterestExpenseDebt"],
        "tax_expense": ["us-gaap:IncomeTaxExpenseBenefit"],
        "ebt": ["us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
        "cost_of_revenue": ["us-gaap:CostOfRevenue", "us-gaap:CostOfGoodsAndServicesSold"],
        "da": ["us-gaap:DepreciationDepletionAndAmortization", "us-gaap:DepreciationAndAmortization"],
        "sbc": ["us-gaap:ShareBasedCompensation", "us-gaap:AllocatedShareBasedCompensationExpense"],
        "dividends": ["us-gaap:PaymentsOfDividends", "us-gaap:PaymentsOfDividendsCommonStock"],
        "short_term_debt": ["us-gaap:DebtCurrent", "us-gaap:ShortTermBorrowings", "us-gaap:LongTermDebtCurrent"],
        "long_term_debt": ["us-gaap:LongTermDebtNoncurrent", "us-gaap:LongTermDebt"],
        "total_debt": ["us-gaap:DebtAndCapitalLeaseObligations", "us-gaap:DebtInstrumentCarryingAmount"],
        "equity": ["us-gaap:StockholdersEquity"],
        "shares": ["us-gaap:WeightedAverageNumberOfSharesOutstandingBasic", "us-gaap:CommonStockSharesOutstanding"],
        "shares_diluted": ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", "us-gaap:WeightedAverageNumberOfSharesOutstandingDiluted"],
        "accounts_payable": ["us-gaap:AccountsPayableCurrent", "us-gaap:AccountsPayableNetCurrent"],
        "research_and_development": ["us-gaap:ResearchAndDevelopmentExpense", "us-gaap:ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"],
    }

    def clean_html(self, html: str) -> str:
        """Removes HTML tags and normalizes whitespace."""
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "lxml")
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        # Get text
        text = soup.get_text(separator=" ")
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_ixbrl_facts(self, html: str) -> Dict[str, Dict[str, Any]]:
        """
        Extracts numerical facts from iXBRL tags, grouped by period.
        Handles both namespaced (ix:nonFraction) and plain (nonfraction) tags.
        """
        if not html:
            return {}
        
        # Use regex for tag names to be namespace-agnostic and case-insensitive
        soup = BeautifulSoup(html, "lxml")
        fact_tags = soup.find_all(re.compile(r'.*nonfraction', re.IGNORECASE))
        
        if not fact_tags:
            logger.debug("ixbrl_retrying_with_xml_parser")
            soup = BeautifulSoup(html, "xml")
            fact_tags = soup.find_all(re.compile(r'.*nonfraction', re.IGNORECASE))

        if not fact_tags:
            logger.warning("no_ixbrl_tags_found_in_filing")
            return {}

        # 1. Map contexts to dates
        contexts = {}
        context_tags = soup.find_all(re.compile(r'.*context', re.IGNORECASE))
        for context in context_tags:
            context_id = context.get("id")
            if not context_id:
                continue
                
            period = context.find(re.compile(r'.*period', re.IGNORECASE))
            if not period:
                continue
                
            instant = period.find(re.compile(r'.*instant', re.IGNORECASE))
            end_date = period.find(re.compile(r'.*endDate', re.IGNORECASE))
            
            date_val = None
            if instant:
                date_val = instant.get_text().strip()
            elif end_date:
                date_val = end_date.get_text().strip()
                
            if date_val:
                match = re.search(r'(\d{4}-\d{2}-\d{2})', date_val)
                if match:
                    contexts[context_id] = match.group(1)

        # 2. Extract facts grouped by date
        facts_by_date = {}
        
        for tag in fact_tags:
            concept = tag.get("name")
            context_ref = tag.get("contextref") or tag.get("contextRef")
            value_str = tag.get_text().strip().replace(",", "")
            
            if not concept or not context_ref or not value_str or value_str == '-':
                continue
                
            clean_concept = concept.split(':')[-1] if ':' in concept else concept
            
            simplified_concept = None
            for internal, tags in self.XBRL_MAPPINGS.items():
                match_found = False
                for t in tags:
                    t_clean = t.split(':')[-1] if ':' in t else t
                    if concept.lower() == t.lower() or clean_concept.lower() == t_clean.lower():
                        match_found = True
                        break
                if match_found:
                    simplified_concept = internal
                    break
            
            if not simplified_concept:
                continue
                
            date_val = contexts.get(context_ref)
            if not date_val:
                continue
                
            try:
                is_negative = False
                if value_str.startswith('(') and value_str.endswith(')'):
                    value_str = value_str[1:-1]
                    is_negative = True
                
                # Cleanup potential non-numeric characters before float conversion
                value_str = re.sub(r'[^\d.]', '', value_str)
                if not value_str:
                    continue
                    
                value = float(value_str)
                if is_negative or tag.get('sign') == '-':
                    value = -abs(value)
                    
                scale = int(tag.get('scale', 0))
                value = value * (10 ** scale)
                
                if date_val not in facts_by_date:
                    facts_by_date[date_val] = {}
                
                if simplified_concept not in facts_by_date[date_val] or \
                   abs(value) > abs(facts_by_date[date_val][simplified_concept]):
                    facts_by_date[date_val][simplified_concept] = value
                    
            except ValueError:
                continue
                
        logger.info("ixbrl_extraction_complete", periods_found=len(facts_by_date))
        return facts_by_date

    def extract_sections(self, html: str) -> Dict[str, str]:
        """
        Extracts major 10-K items as raw HTML chunks.
        Note: This returns the HTML for each section so we can do 
        further processing if needed.
        """
        sections = {}
        
        # Use a more efficient approach for large filings: 
        # identify indices of section headers and split.
        
        # We search for the pattern in the text to find where they start
        text = self.clean_html(html)
        
        positions = []
        for name, pattern in self.SECTIONS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                positions.append((match.start(), name))
        
        # Sort by position in document
        positions.sort()
        
        for i in range(len(positions)):
            start_pos, name = positions[i]
            end_pos = positions[i+1][0] if i + 1 < len(positions) else len(text)
            
            sections[name] = text[start_pos:end_pos].strip()
            
        return sections

    def get_section(self, html: str, section_name: str) -> Optional[str]:
        """Convenience method to get a single section's text."""
        sections = self.extract_sections(html)
        return sections.get(section_name)
