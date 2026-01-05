import asyncio
from dataclasses import dataclass
from typing import List, Optional
from statistics import median
import yfinance as yf
from .fmp_client import FMPClient, FMPClientError


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
    """Analyzes a stock against its peer group using valuation multiples."""
    
    def __init__(self, fmp_client: Optional[FMPClient] = None):
        self.client = fmp_client
    
    async def analyze(self, symbol: str, max_peers: int = 5) -> ComparableResult:
        """
        Run comparable analysis for a stock.
        Uses Yahoo Finance for metrics (more reliable rate limits).
        
        Args:
            symbol: Stock ticker
            max_peers: Maximum number of peers to include
            
        Returns:
            ComparableResult with peer comparison and implied valuations
        """
        loop = asyncio.get_event_loop()
        
        # Get target company data from Yahoo
        target, sector, industry, peer_symbols = await loop.run_in_executor(
            None, self._get_company_data_yahoo, symbol
        )
        
        peer_symbols = peer_symbols[:max_peers]
        
        # Fetch metrics for all peers using Yahoo
        peers = []
        for peer_symbol in peer_symbols:
            try:
                peer = await loop.run_in_executor(
                    None, self._get_metrics_yahoo, peer_symbol
                )
                if peer:
                    peers.append(peer)
            except Exception:
                continue
        
        # Calculate peer medians
        peer_medians = self._calculate_medians(peers)
        
        # Calculate implied valuations
        implied_valuations = self._calculate_implied_valuations(
            target, peer_medians
        )
        
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
    
    # Fallback peer lists by sector
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
    
    def _get_company_data_yahoo(self, symbol: str) -> tuple:
        """Get company data and peers from Yahoo Finance."""
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info or not info.get("regularMarketPrice"):
            raise ValueError(f"No data available for {symbol}")
        
        target = CompanyMetrics(
            symbol=symbol,
            name=info.get("longName") or info.get("shortName") or symbol,
            price=info.get("regularMarketPrice") or info.get("currentPrice"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            price_to_book=info.get("priceToBook"),
            ev_to_revenue=info.get("enterpriseToRevenue"),
        )
        
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")
        
        # Get peer companies from FMP if available
        peer_symbols = []
        if self.client:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                peer_symbols = loop.run_until_complete(self.client.get_stock_peers(symbol))
                loop.close()
            except Exception:
                pass
        
        # Fallback to sector-based peers if FMP fails or returns empty
        if not peer_symbols:
            sector_peers = self.SECTOR_PEERS.get(sector, [])
            # Exclude the target symbol from peers
            peer_symbols = [p for p in sector_peers if p != symbol.upper()]
        
        return target, sector, industry, peer_symbols
    
    def _get_metrics_yahoo(self, symbol: str) -> Optional[CompanyMetrics]:
        """Get valuation metrics for a single stock from Yahoo."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or not info.get("regularMarketPrice"):
                return None
            
            return CompanyMetrics(
                symbol=symbol,
                name=info.get("longName") or info.get("shortName") or symbol,
                price=info.get("regularMarketPrice") or info.get("currentPrice"),
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE"),
                ev_to_ebitda=info.get("enterpriseToEbitda"),
                price_to_sales=info.get("priceToSalesTrailing12Months"),
                price_to_book=info.get("priceToBook"),
                ev_to_revenue=info.get("enterpriseToRevenue"),
            )
        except Exception:
            return None
    
    def _build_company_metrics(
        self, 
        symbol: str, 
        profile: dict, 
        metrics: dict, 
        ratios: dict
    ) -> CompanyMetrics:
        """Build CompanyMetrics from FMP API responses (legacy method)."""
        return CompanyMetrics(
            symbol=symbol,
            name=profile.get("companyName", symbol),
            price=profile.get("price"),
            market_cap=profile.get("marketCap"),
            pe_ratio=ratios.get("peRatioTTM") or metrics.get("peRatioTTM"),
            ev_to_ebitda=metrics.get("enterpriseValueOverEBITDATTM"),
            price_to_sales=ratios.get("priceToSalesRatioTTM") or metrics.get("priceToSalesRatioTTM"),
            price_to_book=ratios.get("priceToBookRatioTTM") or metrics.get("pbRatioTTM"),
            ev_to_revenue=metrics.get("evToSalesTTM"),
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
        """
        Calculate implied price based on each multiple.
        
        For P/E: implied_price = EPS * peer_median_PE
        For P/S: implied_price = revenue_per_share * peer_median_PS
        etc.
        """
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
        
        # EV/EBITDA - more complex, need enterprise value
        if target.ev_to_ebitda and target.price and peer_medians.get("ev_to_ebitda"):
            # We use a simplification: assume EV proportional to price
            # In reality we'd need net debt per share
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

