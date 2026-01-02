"""Pytest configuration and shared fixtures."""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.stock import Stock, StockFundamentals, StockPrice
from app.db.database import Base
from app.db import models  # Import models to register them with Base


@pytest_asyncio.fixture
async def test_db():
    """Create a test database session."""
    # In-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        
    await engine.dispose()


@pytest.fixture
def sample_stock_price() -> StockPrice:
    """Sample stock price data."""
    return StockPrice(
        current=Decimal("150.00"),
        open=Decimal("148.50"),
        high=Decimal("152.00"),
        low=Decimal("147.00"),
        close=Decimal("149.00"),
        volume=10_000_000,
        fifty_two_week_high=Decimal("180.00"),
        fifty_two_week_low=Decimal("120.00"),
    )


@pytest.fixture
def sample_fundamentals_value_stock() -> StockFundamentals:
    """Sample fundamentals for a typical value stock."""
    return StockFundamentals(
        # Valuation
        pe_ratio=Decimal("12.5"),
        pb_ratio=Decimal("1.8"),
        ps_ratio=Decimal("1.2"),
        ev_ebitda=Decimal("8.5"),
        
        # Per share
        eps=Decimal("12.00"),
        book_value_per_share=Decimal("83.33"),
        fcf_per_share=Decimal("10.00"),
        
        # Profitability
        profit_margin=Decimal("15.0"),
        operating_margin=Decimal("18.0"),
        roe=Decimal("14.4"),
        roa=Decimal("8.0"),
        roic=Decimal("12.0"),
        
        # Growth
        revenue_growth=Decimal("5.0"),
        earnings_growth=Decimal("7.0"),
        eps_growth_5y=Decimal("6.0"),
        
        # Balance sheet
        total_debt=Decimal("5_000_000_000"),
        total_cash=Decimal("2_000_000_000"),
        debt_to_equity=Decimal("0.6"),
        current_ratio=Decimal("1.8"),
        interest_coverage=Decimal("12.0"),
        
        # Other
        market_cap=Decimal("50_000_000_000"),
        enterprise_value=Decimal("53_000_000_000"),
        shares_outstanding=333_333_333,
        dividend_yield=Decimal("2.5"),
    )


@pytest.fixture
def sample_fundamentals_growth_stock() -> StockFundamentals:
    """Sample fundamentals for a growth stock."""
    return StockFundamentals(
        pe_ratio=Decimal("45.0"),
        pb_ratio=Decimal("8.0"),
        ps_ratio=Decimal("12.0"),
        
        eps=Decimal("5.00"),
        book_value_per_share=Decimal("28.13"),
        fcf_per_share=Decimal("8.00"),
        
        profit_margin=Decimal("22.0"),
        operating_margin=Decimal("25.0"),
        roe=Decimal("25.0"),
        roic=Decimal("20.0"),
        
        revenue_growth=Decimal("25.0"),
        earnings_growth=Decimal("30.0"),
        eps_growth_5y=Decimal("28.0"),
        
        total_debt=Decimal("1_000_000_000"),
        total_cash=Decimal("5_000_000_000"),
        debt_to_equity=Decimal("0.15"),
        current_ratio=Decimal("3.0"),
        
        market_cap=Decimal("100_000_000_000"),
        shares_outstanding=444_444_444,
    )


@pytest.fixture
def sample_fundamentals_financial() -> StockFundamentals:
    """Sample fundamentals for a financial company (bank)."""
    return StockFundamentals(
        pe_ratio=Decimal("10.0"),
        pb_ratio=Decimal("1.1"),
        
        eps=Decimal("8.00"),
        book_value_per_share=Decimal("72.73"),
        
        roe=Decimal("11.0"),
        roa=Decimal("1.1"),
        
        market_cap=Decimal("80_000_000_000"),
        shares_outstanding=1_000_000_000,
    )


@pytest.fixture
def sample_value_stock(
    sample_stock_price: StockPrice,
    sample_fundamentals_value_stock: StockFundamentals,
) -> Stock:
    """Complete sample value stock."""
    return Stock(
        symbol="VALUE",
        name="Value Corp Inc.",
        sector="Industrials",
        industry="Machinery",
        exchange="NYSE",
        price=sample_stock_price,
        fundamentals=sample_fundamentals_value_stock,
    )


@pytest.fixture
def sample_growth_stock(
    sample_fundamentals_growth_stock: StockFundamentals,
) -> Stock:
    """Complete sample growth stock."""
    return Stock(
        symbol="GROW",
        name="Growth Tech Inc.",
        sector="Technology",
        industry="Software",
        exchange="NASDAQ",
        price=StockPrice(
            current=Decimal("225.00"),
            open=Decimal("220.00"),
            high=Decimal("228.00"),
            low=Decimal("218.00"),
            close=Decimal("222.00"),
            volume=15_000_000,
        ),
        fundamentals=sample_fundamentals_growth_stock,
    )


@pytest.fixture
def sample_financial_stock(
    sample_fundamentals_financial: StockFundamentals,
) -> Stock:
    """Complete sample financial stock."""
    return Stock(
        symbol="BANK",
        name="Big Bank Corp",
        sector="Financials",
        industry="Banks",
        exchange="NYSE",
        price=StockPrice(
            current=Decimal("80.00"),
            open=Decimal("79.00"),
            high=Decimal("81.00"),
            low=Decimal("78.50"),
            close=Decimal("79.50"),
            volume=8_000_000,
        ),
        fundamentals=sample_fundamentals_financial,
    )

