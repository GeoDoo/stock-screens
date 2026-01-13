import pytest
from app.services.technical_indicators import TechnicalIndicators

def test_vw_macd():
    # Simple case: constant price and volume
    prices = [100.0] * 50
    volumes = [1000] * 50
    macd_line, signal_line, hist = TechnicalIndicators.vw_macd(prices, volumes)
    
    # Should be 0 for constant price
    assert all(m == 0 or m is None for m in macd_line)
    assert all(s == 0 or s is None for s in signal_line)

def test_v_rsi():
    # Simple case: constant price
    prices = [100.0] * 20
    volumes = [1000] * 20
    rsi = TechnicalIndicators.v_rsi(prices, volumes, period=14)
    
    # Should be 50 or None for constant price
    latest_rsi = next((v for v in reversed(rsi) if v is not None), None)
    assert latest_rsi == 50.0 or latest_rsi is None
