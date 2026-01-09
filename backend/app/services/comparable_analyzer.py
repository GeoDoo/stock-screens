import asyncio
from dataclasses import dataclass
from typing import List, Optional
from statistics import median

from .stock_data_client import StockDataClient
from .data_adapter import stock_data_to_legacy


@dataclass
class CompanyMetrics:
    """Key valuation metrics for a company."""
    symbol: str
    name: str
    price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    ev_to_revenue: Optional[float] = None
    # Additional fields for proper EV/EBITDA implied price calculation
    # (needed to bridge from EV to Equity correctly)
    ebitda: Optional[float] = None
    net_debt: Optional[float] = None
    shares_outstanding: Optional[float] = None
    

@dataclass
class ImpliedValuation:
    """Implied price based on a specific multiple."""
    metric_name: str
    peer_median: Optional[float]
    company_value: Optional[float]
    implied_price: Optional[float]
    upside_percent: Optional[float]


@dataclass
class ComparableResult:
    """Complete comparable analysis result."""
    target: CompanyMetrics
    peers: List[CompanyMetrics]
    sector: str
    industry: str
    peer_medians: dict
    implied_valuations: List[ImpliedValuation]
    average_implied_price: Optional[float]
    average_upside: Optional[float]


class ComparableAnalyzer:
    """
    Analyzes a stock against its peer group using valuation multiples.
    
    Uses the same provider as all other analyses for consistency.
    Prefers industry-level peers for more accurate comparisons.
    """
    
    # Sub-industry peer groups for precise comparable analysis
    # These match FMP/Yahoo industry classifications
    INDUSTRY_PEERS = {
        # Technology - Hardware
        "Consumer Electronics": ["AAPL", "SNE", "HPQ", "DELL", "LOGI", "SONO", "GPRO"],
        "Computer Hardware": ["AAPL", "HPQ", "DELL", "LOGI", "NTAP", "WDC", "STX"],
        
        # Technology - Software  
        "Software—Infrastructure": ["MSFT", "ORCL", "CRM", "NOW", "SNOW", "MDB", "DDOG", "NET"],
        "Software—Application": ["ADBE", "INTU", "WDAY", "TEAM", "ZM", "DOCU", "HUBS", "PANW"],
        
        # Technology - Internet
        "Internet Content & Information": ["GOOGL", "META", "SNAP", "PINS", "TWTR", "MTCH", "YELP"],
        "Internet Retail": ["AMZN", "EBAY", "ETSY", "W", "CHWY", "BABA", "JD", "PDD"],
        
        # Technology - Semiconductors
        "Semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU", "LRCX", "AMAT"],
        "Semiconductor Equipment & Materials": ["ASML", "LRCX", "AMAT", "KLAC", "TER", "MKSI"],
        
        # Financial Services
        "Banks—Diversified": ["JPM", "BAC", "WFC", "C", "USB", "PNC", "TFC", "COF"],
        "Banks—Regional": ["USB", "PNC", "TFC", "FITB", "RF", "KEY", "CFG", "MTB"],
        "Capital Markets": ["GS", "MS", "SCHW", "BLK", "BX", "KKR", "APO", "IBKR"],
        "Credit Services": ["V", "MA", "AXP", "DFS", "COF", "SYF", "PYPL"],
        "Insurance—Diversified": ["BRK.B", "AIG", "MET", "PRU", "AFL", "PGR", "TRV"],
        "Asset Management": ["BLK", "BX", "KKR", "APO", "TROW", "IVZ", "BEN"],
        
        # Healthcare
        "Drug Manufacturers—General": ["JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "GSK", "AZN"],
        "Biotechnology": ["AMGN", "GILD", "REGN", "VRTX", "BIIB", "MRNA", "BNTX", "ILMN"],
        "Medical Devices": ["MDT", "ABT", "SYK", "BSX", "ISRG", "EW", "ZBH", "DXCM"],
        "Healthcare Plans": ["UNH", "ELV", "CI", "HUM", "CNC", "MOH"],
        "Medical Instruments & Supplies": ["TMO", "DHR", "BDX", "BAX", "A", "MTD", "IQV"],
        
        # Consumer Cyclical
        "Auto Manufacturers": ["TSLA", "GM", "F", "TM", "HMC", "RIVN", "LCID", "NIO"],
        "Restaurants": ["MCD", "SBUX", "YUM", "CMG", "DRI", "DARDEN", "QSR", "DPZ"],
        "Specialty Retail": ["HD", "LOW", "TJX", "ROST", "ULTA", "BBY", "FIVE", "OLLI"],
        "Apparel Retail": ["TJX", "ROST", "GPS", "ANF", "AEO", "URBN", "LULU"],
        "Footwear & Accessories": ["NKE", "ADDYY", "UAA", "SKX", "CROX", "DECK", "VFC"],
        "Travel & Leisure": ["BKNG", "EXPE", "ABNB", "MAR", "HLT", "H", "LVS", "WYNN"],
        
        # Communication Services
        "Entertainment": ["DIS", "NFLX", "WBD", "PARA", "LGF.A", "CMCSA", "FOXA"],
        "Telecom Services": ["VZ", "T", "TMUS", "CHTR", "LBRDK"],
        "Electronic Gaming & Multimedia": ["EA", "TTWO", "ATVI", "RBLX", "U", "SE"],
        
        # Consumer Defensive
        "Beverages—Non-Alcoholic": ["KO", "PEP", "MNST", "KDP", "CELH"],
        "Household & Personal Products": ["PG", "CL", "KMB", "CLX", "CHD", "EL"],
        "Discount Stores": ["WMT", "COST", "TGT", "DG", "DLTR", "BJ"],
        "Tobacco": ["PM", "MO", "BTI", "IMBBY"],
        
        # Energy
        "Oil & Gas Integrated": ["XOM", "CVX", "SHEL", "TTE", "BP", "COP"],
        "Oil & Gas E&P": ["EOG", "PXD", "DVN", "FANG", "OXY", "MRO", "APA"],
        "Oil & Gas Equipment & Services": ["SLB", "HAL", "BKR", "NOV", "FTI"],
        "Oil & Gas Refining & Marketing": ["MPC", "PSX", "VLO", "PBF", "DK"],
        
        # Industrials
        "Aerospace & Defense": ["BA", "RTX", "LMT", "NOC", "GD", "HII", "TDG", "HEI"],
        "Farm & Heavy Construction Machinery": ["DE", "CAT", "AGCO", "CNHI", "PCAR"],
        "Railroads": ["UNP", "CSX", "NSC", "CP", "CNI"],
        "Airlines": ["DAL", "UAL", "LUV", "AAL", "ALK", "JBLU"],
        "Air Freight & Logistics": ["UPS", "FDX", "EXPD", "XPO", "CHRW"],
        
        # Real Estate
        "REIT—Data Center": ["EQIX", "DLR", "AMT", "CCI"],
        "REIT—Industrial": ["PLD", "PSA", "EXR", "CUBE"],
        "REIT—Residential": ["AVB", "EQR", "MAA", "UDR", "INVH"],
        "REIT—Retail": ["SPG", "O", "KIM", "REG", "FRT"],
        
        # Utilities
        "Utilities—Regulated Electric": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "XEL", "WEC"],
        "Utilities—Renewable": ["NEE", "AES", "BEP", "CWEN", "RUN"],
    }
    
    # Fallback peer lists by sector (used when industry has no defined peers)
    SECTOR_PEERS = {
        "Technology": ["MSFT", "GOOGL", "META", "NVDA", "AAPL", "ORCL", "CRM", "ADBE", "INTC", "AMD"],
        "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V"],
        "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY"],
        "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "TJX", "BKNG"],
        "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA"],
        "Consumer Defensive": ["WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "CL", "KHC", "GIS"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "Industrials": ["UPS", "HON", "UNP", "BA", "CAT", "GE", "RTX", "LMT", "DE", "MMM"],
        "Basic Materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "DD", "DOW", "PPG"],
        "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "WELL", "DLR", "AVB"],
        "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "ED", "WEC"],
    }
    
    def __init__(self, client: StockDataClient, provider: str):
        """
        Initialize with a configured StockDataClient.
        
        Args:
            client: StockDataClient configured with the user's chosen provider
            provider: Name of the provider being used (for FMP-specific features)
        """
        self.client = client
        self.provider = provider
    
    async def analyze(self, symbol: str, max_peers: int = 5) -> ComparableResult:
        """
        Run comparable analysis for a stock.
        
        Args:
            symbol: Stock ticker
            max_peers: Maximum number of peers to include
            
        Returns:
            ComparableResult with peer comparison and implied valuations
        """
        # Get target company data
        stock_data = await self.client.get_stock_data(symbol)
        data = stock_data_to_legacy(stock_data)
        
        target = self._extract_metrics(symbol, data)
        
        sector = data.get("profile", {}).get("sector", "Unknown")
        industry = data.get("profile", {}).get("industry", "Unknown")
        
        # Get peer companies - prefer industry-level, fall back to sector
        peer_symbols = self._get_peers(symbol, sector, industry)[:max_peers]
        
        # Fetch metrics for all peers using the SAME provider
        peers = []
        for peer_symbol in peer_symbols:
            try:
                peer_stock_data = await self.client.get_stock_data(peer_symbol)
                peer_data = stock_data_to_legacy(peer_stock_data)
                peer = self._extract_metrics(peer_symbol, peer_data)
                peers.append(peer)
            except Exception:
                # Skip peers with missing data
                continue
        
        # Calculate peer medians
        peer_medians = self._calculate_medians(peers)
        
        # Calculate implied valuations
        implied_valuations = self._calculate_implied_valuations(target, peer_medians)
        
        # Average implied price
        valid_implied = [iv.implied_price for iv in implied_valuations if iv.implied_price]
        average_implied = median(valid_implied) if valid_implied else None
        
        # Average upside
        average_upside = None
        if average_implied and target.price:
            average_upside = ((average_implied - target.price) / target.price) * 100
        
        return ComparableResult(
            target=target,
            peers=peers,
            sector=sector,
            industry=industry,
            peer_medians=peer_medians,
            implied_valuations=implied_valuations,
            average_implied_price=average_implied,
            average_upside=average_upside,
        )
    
    def _get_peers(self, symbol: str, sector: str, industry: str) -> List[str]:
        """
        Get peer companies, preferring industry-level over sector-level.
        
        Args:
            symbol: Target stock ticker
            sector: Company sector (fallback)
            industry: Company industry (preferred)
            
        Returns:
            List of peer symbols, excluding the target
        """
        symbol_upper = symbol.upper()
        
        # Try industry-level peers first (more precise)
        industry_peers = self.INDUSTRY_PEERS.get(industry, [])
        if industry_peers:
            return [p for p in industry_peers if p != symbol_upper]
        
        # Fall back to sector-level peers
        sector_peers = self.SECTOR_PEERS.get(sector, [])
        return [p for p in sector_peers if p != symbol_upper]
    
    def _get_peer_source(self, sector: str, industry: str) -> str:
        """
        Determine whether peers will come from industry or sector mapping.
        
        Returns:
            "industry" or "sector"
        """
        if industry in self.INDUSTRY_PEERS:
            return "industry"
        return "sector"
    
    def _get_sector_peers(self, symbol: str, sector: str) -> List[str]:
        """Get peer companies for a given sector, excluding the target.
        
        DEPRECATED: Use _get_peers() instead for industry-aware selection.
        """
        sector_peers = self.SECTOR_PEERS.get(sector, [])
        return [p for p in sector_peers if p != symbol.upper()]
    
    def _extract_metrics(self, symbol: str, data: dict) -> CompanyMetrics:
        """Extract valuation metrics from stock data."""
        profile = data.get("profile", {})
        
        # Get basic info
        price = profile.get("price")
        market_cap = profile.get("marketCap")
        shares = profile.get("sharesOutstanding")
        
        # Calculate ratios from financial data
        financials = data.get("income_statement", [])
        balance_sheet = data.get("balance_sheet", [])
        cash_flow = data.get("cash_flow", [])
        
        pe_ratio = None
        price_to_sales = None
        price_to_book = None
        ev_to_ebitda = None
        ev_to_revenue = None
        ebitda_calc = None
        net_debt_calc = None
        
        if financials and price and market_cap:
            latest = financials[0] if financials else {}
            latest_bs = balance_sheet[0] if balance_sheet else {}
            latest_cf = cash_flow[0] if cash_flow else {}
            
            # P/E ratio
            net_income = latest.get("netIncome")
            if net_income and shares and net_income > 0:
                eps = net_income / shares
                pe_ratio = price / eps if eps > 0 else None
            
            # P/S ratio
            revenue = latest.get("revenue")
            if revenue and shares and revenue > 0:
                revenue_per_share = revenue / shares
                price_to_sales = price / revenue_per_share if revenue_per_share > 0 else None
            
            # P/B ratio
            total_equity = latest_bs.get("totalStockholdersEquity") or latest_bs.get("totalEquity")
            if total_equity and shares and total_equity > 0:
                book_per_share = total_equity / shares
                price_to_book = price / book_per_share if book_per_share > 0 else None
            
            # EV/EBITDA - calculate component values for proper implied price later
            total_debt = latest_bs.get("totalDebt") or 0
            cash = latest_bs.get("cashAndCashEquivalents") or latest_bs.get("cashAndShortTermInvestments") or 0
            net_debt_calc = total_debt - cash
            enterprise_value = market_cap + net_debt_calc
            
            operating_income = latest.get("operatingIncome")
            # D&A comes from cash_flow, not income_statement
            # (stock_data_to_legacy places it in cash_flow)
            da = latest_cf.get("depreciationAndAmortization") or 0
            if operating_income:
                ebitda_calc = operating_income + da
                if ebitda_calc > 0:
                    ev_to_ebitda = enterprise_value / ebitda_calc
                    ev_to_revenue = enterprise_value / revenue if revenue and revenue > 0 else None
        
        return CompanyMetrics(
            symbol=symbol,
            name=profile.get("companyName", symbol),
            price=price,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            ev_to_ebitda=ev_to_ebitda,
            price_to_sales=price_to_sales,
            price_to_book=price_to_book,
            ev_to_revenue=ev_to_revenue,
            # Additional fields for proper EV-to-Equity bridge
            ebitda=ebitda_calc,
            net_debt=net_debt_calc,
            shares_outstanding=shares,
        )
    
    def _calculate_medians(self, peers: List[CompanyMetrics]) -> dict:
        """Calculate median values for each metric across peers."""
        def safe_median(values):
            valid = [v for v in values if v is not None and v > 0]
            return median(valid) if valid else None
        
        return {
            "pe_ratio": safe_median([p.pe_ratio for p in peers]),
            "ev_to_ebitda": safe_median([p.ev_to_ebitda for p in peers]),
            "price_to_sales": safe_median([p.price_to_sales for p in peers]),
            "price_to_book": safe_median([p.price_to_book for p in peers]),
            "ev_to_revenue": safe_median([p.ev_to_revenue for p in peers]),
        }
    
    def _calculate_implied_valuations(
        self, 
        target: CompanyMetrics, 
        peer_medians: dict
    ) -> List[ImpliedValuation]:
        """Calculate implied price based on each multiple."""
        valuations = []
        
        # P/E implied valuation
        if target.pe_ratio and target.price and peer_medians.get("pe_ratio"):
            eps = target.price / target.pe_ratio
            implied = eps * peer_medians["pe_ratio"]
            upside = ((implied - target.price) / target.price) * 100 if target.price else None
            valuations.append(ImpliedValuation(
                metric_name="P/E",
                peer_median=peer_medians["pe_ratio"],
                company_value=target.pe_ratio,
                implied_price=implied,
                upside_percent=upside,
            ))
        
        # P/S implied valuation
        if target.price_to_sales and target.price and peer_medians.get("price_to_sales"):
            sales_per_share = target.price / target.price_to_sales
            implied = sales_per_share * peer_medians["price_to_sales"]
            upside = ((implied - target.price) / target.price) * 100 if target.price else None
            valuations.append(ImpliedValuation(
                metric_name="P/S",
                peer_median=peer_medians["price_to_sales"],
                company_value=target.price_to_sales,
                implied_price=implied,
                upside_percent=upside,
            ))
        
        # P/B implied valuation
        if target.price_to_book and target.price and peer_medians.get("price_to_book"):
            book_per_share = target.price / target.price_to_book
            implied = book_per_share * peer_medians["price_to_book"]
            upside = ((implied - target.price) / target.price) * 100 if target.price else None
            valuations.append(ImpliedValuation(
                metric_name="P/B",
                peer_median=peer_medians["price_to_book"],
                company_value=target.price_to_book,
                implied_price=implied,
                upside_percent=upside,
            ))
        
        # EV/EBITDA implied valuation - use proper EV-to-Equity bridge
        # NOT the "ratio of ratios" shortcut which is invalid for leveraged companies
        if (target.ev_to_ebitda and target.price and peer_medians.get("ev_to_ebitda")
            and target.ebitda and target.net_debt is not None and target.shares_outstanding):
            # Correct method:
            # 1. Implied EV = Peer EV/EBITDA × Target EBITDA
            # 2. Implied Equity = Implied EV - Target Net Debt
            # 3. Implied Price = Implied Equity / Shares
            implied_ev = peer_medians["ev_to_ebitda"] * target.ebitda
            implied_equity = implied_ev - target.net_debt
            implied = implied_equity / target.shares_outstanding if target.shares_outstanding > 0 else None
            
            upside = ((implied - target.price) / target.price) * 100 if target.price and implied else None
            valuations.append(ImpliedValuation(
                metric_name="EV/EBITDA",
                peer_median=peer_medians["ev_to_ebitda"],
                company_value=target.ev_to_ebitda,
                implied_price=implied,
                upside_percent=upside,
            ))
        
        return valuations
