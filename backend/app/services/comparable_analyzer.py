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
    """
    
    # Fallback peer lists by sector (used when provider doesn't have peer data)
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
        
        # Get peer companies based on sector
        peer_symbols = self._get_sector_peers(symbol, sector)[:max_peers]
        
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
    
    def _get_sector_peers(self, symbol: str, sector: str) -> List[str]:
        """Get peer companies for a given sector, excluding the target."""
        sector_peers = self.SECTOR_PEERS.get(sector, [])
        return [p for p in sector_peers if p != symbol.upper()]
    
    def _extract_metrics(self, symbol: str, data: dict) -> CompanyMetrics:
        """Extract valuation metrics from stock data."""
        profile = data.get("profile", {})
        
        # Get basic info
        price = profile.get("price")
        market_cap = profile.get("marketCap")
        
        # Calculate ratios from financial data
        financials = data.get("income_statement", [])
        balance_sheet = data.get("balance_sheet", [])
        cash_flow = data.get("cash_flow", [])
        
        pe_ratio = None
        price_to_sales = None
        price_to_book = None
        ev_to_ebitda = None
        ev_to_revenue = None
        
        if financials and price and market_cap:
            latest = financials[0] if financials else {}
            latest_bs = balance_sheet[0] if balance_sheet else {}
            latest_cf = cash_flow[0] if cash_flow else {}
            
            # P/E ratio
            net_income = latest.get("netIncome")
            shares = profile.get("sharesOutstanding")
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
            
            # EV/EBITDA
            total_debt = latest_bs.get("totalDebt") or 0
            cash = latest_bs.get("cashAndCashEquivalents") or latest_bs.get("cashAndShortTermInvestments") or 0
            enterprise_value = market_cap + total_debt - cash
            
            operating_income = latest.get("operatingIncome")
            # D&A comes from cash_flow, not income_statement
            # (stock_data_to_legacy places it in cash_flow)
            da = latest_cf.get("depreciationAndAmortization") or 0
            if operating_income:
                ebitda = operating_income + da
                if ebitda > 0:
                    ev_to_ebitda = enterprise_value / ebitda
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
        
        # EV/EBITDA implied valuation
        if target.ev_to_ebitda and target.price and peer_medians.get("ev_to_ebitda"):
            ratio_diff = peer_medians["ev_to_ebitda"] / target.ev_to_ebitda if target.ev_to_ebitda else 1
            implied = target.price * ratio_diff
            upside = ((implied - target.price) / target.price) * 100 if target.price else None
            valuations.append(ImpliedValuation(
                metric_name="EV/EBITDA",
                peer_median=peer_medians["ev_to_ebitda"],
                company_value=target.ev_to_ebitda,
                implied_price=implied,
                upside_percent=upside,
            ))
        
        return valuations
