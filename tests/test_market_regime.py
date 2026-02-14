import pandas as pd
from src.analysis.market_regime import MarketRegimeDetector


def test_trending_detection():
    det = MarketRegimeDetector()
    df = pd.DataFrame([
        {"ADX": 30, "BB_Upper": 110, "BB_Lower": 90, "BB_Middle": 100, "RSI": 55, "VWAP": 100, "close": 100},
        {"ADX": 31, "BB_Upper": 120, "BB_Lower": 80, "BB_Middle": 100, "RSI": 60, "VWAP": 100, "close": 102},
    ])
    res = det.detect_regime(df)
    assert res["regime"] == "TRENDING"
    assert res["is_no_trade_zone"] is False


def test_ranging_detection():
    det = MarketRegimeDetector()
    # Narrow bands and low ADX
    df = pd.DataFrame([
        {"ADX": 18, "BB_Upper": 101, "BB_Lower": 99, "BB_Middle": 100, "RSI": 50, "VWAP": 100, "close": 100},
        {"ADX": 18, "BB_Upper": 101, "BB_Lower": 99, "BB_Middle": 100, "RSI": 48, "VWAP": 100, "close": 100},
    ])
    res = det.detect_regime(df)
    assert res["regime"] == "RANGING"


def test_no_trade_zone_detection():
    det = MarketRegimeDetector()
    # 5 rows to enable 4h check; very small movement, RSI ~50, VWAP close
    rows = []
    for i in range(5):
        rows.append({"ADX": 15, "BB_Upper": 101, "BB_Lower": 99, "BB_Middle": 100,
                     "RSI": 50, "VWAP": 100, "close": 100 + i * 0.1})
    df = pd.DataFrame(rows)
    res = det.detect_regime(df)
    assert res["is_no_trade_zone"] is True
