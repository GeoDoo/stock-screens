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
    # Currency for normalization in cross-currency comparisons
    currency: str = "USD"
    

@dataclass
class ImpliedValuation:
    """Implied price based on a specific multiple."""
    metric_name: str
    peer_median: Optional[float]
    company_value: Optional[float]
    implied_price: Optional[float]
    upside_percent: Optional[float]


@dataclass
class CurrencyConversion:
    """
    Currency conversion info for a peer.
    
    P1.3 Fix: Conversions are marked as approximate when using fallback rates.
    """
    symbol: str
    original_currency: str
    converted_to: str
    rate: float  # Units of original currency per unit of target currency
    is_approximate: bool = True  # P1.3: True if using hardcoded fallback rates


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
    # Currency normalization info
    base_currency: str = "USD"  # Currency all values are normalized to
    currency_conversions: Optional[List[CurrencyConversion]] = None  # Peers that needed conversion
    # P1.3: Warn if any FX rates were approximate
    fx_rates_approximate: bool = False  # True if any peer used approximate FX rates


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
        
        # Basic Materials
        "Specialty Chemicals": ["LIN", "APD", "SHW", "ECL", "PPG", "DD", "EMN", "ALB"],
        "Agricultural Inputs": ["MOS", "NTR", "CF", "FMC", "CTVA", "SMG"],
        "Steel": ["NUE", "STLD", "CLF", "X", "RS", "CMC"],
        "Gold": ["NEM", "GOLD", "AEM", "FNV", "WPM", "RGLD"],
        "Copper": ["FCX", "SCCO", "TECK", "HBM"],
        "Aluminum": ["AA", "CENX", "ARNC"],
        "Chemicals": ["DOW", "LYB", "CE", "MEOH", "WLK", "OLN"],
        "Building Materials": ["VMC", "MLM", "SUM", "EXP", "USCR"],
        "Paper & Paper Products": ["IP", "PKG", "WRK", "GPK", "SON"],
        
        # Insurance - Additional
        "Insurance—Life": ["MET", "PRU", "AFL", "LNC", "PFG", "VOYA"],
        "Insurance—Property & Casualty": ["TRV", "ALL", "PGR", "CB", "HIG", "CNA"],
        "Insurance—Specialty": ["AON", "MMC", "WTW", "AJG", "BRO"],
        
        # Additional Consumer industries
        "Packaged Foods": ["GIS", "K", "CAG", "CPB", "SJM", "HRL", "TSN", "HSY"],
        "Beverages—Alcoholic": ["BUD", "STZ", "TAP", "SAM", "DEO"],
        "Grocery Stores": ["KR", "ACI", "SFM", "GO", "WMK"],
        "Home Improvement Retail": ["HD", "LOW", "TSCO", "FND", "WSM"],
        "Luxury Goods": ["RMS", "LVMUY", "CFR", "TPR", "CPRI", "RL"],
        
        # Additional Tech
        "Information Technology Services": ["IBM", "ACN", "CTSH", "EPAM", "GLOB", "DXC"],
        "Electronic Components": ["APH", "TEL", "GLW", "JBL", "FLEX", "CLS"],
        "Communication Equipment": ["CSCO", "ANET", "HPE", "JNPR", "NOK", "ERIC"],
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
        target_currency = target.currency
        
        sector = data.get("profile", {}).get("sector", "Unknown")
        industry = data.get("profile", {}).get("industry", "Unknown")
        
        # Get peer companies - prefer industry-level, fall back to sector
        peer_symbols = self._get_peers(symbol, sector, industry)[:max_peers]
        
        # Fetch metrics for all peers using the SAME provider
        raw_peers = []
        for peer_symbol in peer_symbols:
            try:
                peer_stock_data = await self.client.get_stock_data(peer_symbol)
                peer_data = stock_data_to_legacy(peer_stock_data)
                peer = self._extract_metrics(peer_symbol, peer_data)
                raw_peers.append(peer)
            except Exception:
                # Skip peers with missing data
                continue
        
        # Collect unique currencies that need conversion
        currencies_needed = set()
        for peer in raw_peers:
            if peer.currency != target_currency:
                currencies_needed.add(peer.currency)
        if target_currency != "USD":
            currencies_needed.add(target_currency)
        
        # Fetch exchange rates if we have cross-currency peers
        exchange_rates = {"USD": 1.0}  # USD is always 1.0
        if currencies_needed:
            exchange_rates.update(await self._get_exchange_rates(list(currencies_needed)))
        
        # Normalize peers to target currency
        peers = []
        currency_conversions = []
        for peer in raw_peers:
            if peer.currency != target_currency:
                # Track the conversion - store the actual conversion factor used
                source_rate = exchange_rates.get(peer.currency, 1.0)
                target_rate = exchange_rates.get(target_currency, 1.0)
                if source_rate != 0:
                    # Conversion factor: target_rate / source_rate
                    # e.g., JPY→USD: 1/150 = 0.00667 (multiply JPY by this to get USD)
                    effective_rate = target_rate / source_rate
                else:
                    effective_rate = 1.0
                
                currency_conversions.append(CurrencyConversion(
                    symbol=peer.symbol,
                    original_currency=peer.currency,
                    converted_to=target_currency,
                    rate=effective_rate,
                ))
                
                # Normalize the peer
                peer = self._normalize_to_currency(peer, target_currency, exchange_rates)
            
            peers.append(peer)
        
        # Calculate peer medians (now all in same currency)
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
            base_currency=target_currency,
            currency_conversions=currency_conversions if currency_conversions else None,
            # P1.3: Mark if any conversions used approximate rates
            fx_rates_approximate=any(c.is_approximate for c in currency_conversions) if currency_conversions else False,
        )
    
    async def _get_exchange_rates(self, currencies: List[str]) -> dict:
        """
        Get exchange rates for a list of currencies vs USD.
        
        Returns dict mapping currency code to rate (units per 1 USD).
        For example: {"EUR": 0.92, "GBP": 0.79, "JPY": 150}
        
        P1.3 Note: Currently uses hardcoded APPROXIMATE rates.
        These should be treated as rough estimates only.
        For institutional use, integrate a live FX API (e.g., exchangerate-api.com).
        """
        # APPROXIMATE fallback rates (last updated: January 2026)
        # P1.3: These are approximate - all conversions using these are marked is_approximate=True
        # These are "units per 1 USD"
        fallback_rates = {
            "EUR": 0.92,
            "GBP": 0.79,
            "JPY": 149.0,
            "CHF": 0.88,
            "CAD": 1.36,
            "AUD": 1.53,
            "CNY": 7.24,
            "HKD": 7.82,
            "KRW": 1320.0,
            "INR": 83.0,
            "BRL": 4.97,
            "MXN": 17.2,
            "SGD": 1.34,
            "SEK": 10.4,
            "NOK": 10.6,
            "DKK": 6.87,
            "NZD": 1.63,
            "ZAR": 18.7,
            "RUB": 92.0,
            "TRY": 32.0,
            "PLN": 4.0,
            "TWD": 31.5,
            "THB": 35.0,
            "IDR": 15700.0,
            "MYR": 4.7,
            "PHP": 56.0,
            "CZK": 23.0,
            "ILS": 3.7,
            "CLP": 900.0,
            "COP": 4000.0,
            "PEN": 3.7,
            "ARS": 870.0,
        }
        
        result = {}
        for currency in currencies:
            if currency == "USD":
                result["USD"] = 1.0
            elif currency in fallback_rates:
                result[currency] = fallback_rates[currency]
            else:
                # Unknown currency - assume 1:1 with USD (will be wrong but safe)
                result[currency] = 1.0
        
        return result
    
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
        
        # Normalize industry name: convert regular hyphens to em-dashes
        # Different providers use different dash characters
        normalized_industry = industry.replace("-", "—") if industry else ""
        
        # Try industry-level peers first (more precise)
        # Check both original and normalized names
        industry_peers = (
            self.INDUSTRY_PEERS.get(industry, []) or
            self.INDUSTRY_PEERS.get(normalized_industry, [])
        )
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
        # Normalize industry name: convert regular hyphens to em-dashes
        normalized_industry = industry.replace("-", "—") if industry else ""
        
        if industry in self.INDUSTRY_PEERS or normalized_industry in self.INDUSTRY_PEERS:
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
            # Currency for cross-currency normalization
            currency=profile.get("currency", "USD"),
        )
    
    def _normalize_to_currency(
        self,
        metrics: CompanyMetrics,
        target_currency: str,
        exchange_rates: dict,
    ) -> CompanyMetrics:
        """
        Normalize a company's absolute values to a target currency.
        
        Args:
            metrics: CompanyMetrics to normalize
            target_currency: Currency to convert to (e.g., "USD")
            exchange_rates: Dict mapping currency codes to rate vs USD
                           e.g., {"EUR": 0.92, "GBP": 0.79, "JPY": 150}
                           Rate = how many units of currency = 1 USD
        
        Returns:
            New CompanyMetrics with absolute values converted to target currency
        
        Note:
            - Ratios (P/E, EV/EBITDA, etc.) are currency-agnostic and unchanged
            - Absolute values (market_cap, ebitda, etc.) are converted
            - If currency matches target, no conversion needed
            - If no rate available, values remain unchanged
        """
        source_currency = metrics.currency
        
        # No conversion needed if already in target currency
        if source_currency == target_currency:
            return metrics
        
        # Calculate conversion factor
        # We convert: source → USD → target
        # rate = how many units = 1 USD
        source_rate = exchange_rates.get(source_currency, 1.0)  # 1.0 for USD
        target_rate = exchange_rates.get(target_currency, 1.0)
        
        # For source currency: value_usd = value_source / source_rate
        # For target currency: value_target = value_usd * target_rate
        # Combined: value_target = value_source * (target_rate / source_rate)
        
        # If source is JPY (150/USD) and target is USD (1/USD):
        # conversion = 1 / 150 = 0.00667 (divide JPY by 150 to get USD)
        if source_rate == 0:
            conversion_factor = 1.0  # Fallback to no conversion
        else:
            conversion_factor = target_rate / source_rate
        
        def convert(value: Optional[float]) -> Optional[float]:
            return value * conversion_factor if value is not None else None
        
        return CompanyMetrics(
            symbol=metrics.symbol,
            name=metrics.name,
            # Absolute values - need conversion
            price=convert(metrics.price),
            market_cap=convert(metrics.market_cap),
            ebitda=convert(metrics.ebitda),
            net_debt=convert(metrics.net_debt),
            # Ratios - currency agnostic, no conversion
            pe_ratio=metrics.pe_ratio,
            ev_to_ebitda=metrics.ev_to_ebitda,
            price_to_sales=metrics.price_to_sales,
            price_to_book=metrics.price_to_book,
            ev_to_revenue=metrics.ev_to_revenue,
            # Shares - not a currency value
            shares_outstanding=metrics.shares_outstanding,
            # Update currency
            currency=target_currency,
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
