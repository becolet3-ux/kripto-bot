import time
import math
from src.strategies.multi_timeframe import fetch_data, analyze_single_timeframe, multi_timeframe_analyzer


class FakeExchangeGood:
    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        base = 100.0 if timeframe == "15m" else (101.0 if timeframe == "1h" else 102.0)
        now = int(time.time() * 1000)
        data = []
        for i in range(limit):
            close = base + i * 0.1
            high = close + 0.2
            low = close - 0.2
            open_ = close - 0.05
            vol = 10 + i
            data.append([now - (limit - i) * 60_000, open_, high, low, close, vol])
        return data


class FakeExchangeUnknown:
    pass


class FakeExchangeException:
    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        raise RuntimeError("boom")


def test_fetch_data_unknown_exchange():
    df = fetch_data("AAA/USDT", "1h", FakeExchangeUnknown())
    assert df is None


def test_fetch_data_exception_handled():
    df = fetch_data("AAA/USDT", "1h", FakeExchangeException())
    assert df is None


def test_analyze_single_timeframe_smoke():
    res = analyze_single_timeframe("AAA/USDT", "1h", FakeExchangeGood())
    assert isinstance(res, dict)
    assert "direction" in res and "trend_strength" in res


def test_multi_timeframe_analyzer_structure():
    res = multi_timeframe_analyzer("AAA/USDT", FakeExchangeGood())
    assert "consensus" in res and "direction" in res and "timeframes" in res
