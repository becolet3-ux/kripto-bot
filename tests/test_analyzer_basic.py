import numpy as np
from datetime import datetime, timedelta
from src.strategies.analyzer import MarketAnalyzer


def make_candles(n=60, base=100.0, step=0.2):
    base_time = datetime.utcnow() - timedelta(hours=n)
    candles = []
    for i in range(n):
        t = int((base_time + timedelta(hours=i)).timestamp() * 1000)
        c = base + i * step
        o = c * 0.999
        h = c * 1.01
        l = c * 0.99
        v = 1000.0
        candles.append([t, o, h, l, c, v])
    return candles


def test_analyzer_calculate_indicators_non_empty():
    ma = MarketAnalyzer()
    candles = make_candles(80)
    df = ma.calculate_indicators(candles)
    assert not df.empty
    # Basic columns expected
    for col in ["EMA_Short", "EMA_Long", "RSI", "BB_Upper", "MACD", "ATR"]:
        assert col in df.columns


def test_analyze_market_regime_returns_fields():
    ma = MarketAnalyzer()
    # Create wider bands by amplifying step
    candles = make_candles(120, base=100.0, step=1.0)
    res = ma.analyze_market_regime(candles)
    assert "trend" in res and "volatility" in res
