import asyncio
import time
import pytest
from src.collectors.binance_loader import BinanceDataLoader


class FakeExchange:
    def __init__(self):
        self.calls = 0

    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        self.calls += 1
        now = int(time.time() * 1000)
        data = []
        base = 100.0
        for i in range(limit):
            ts = now - (limit - i) * 3600000
            o = base + i * 0.1
            h = o + 0.2
            l = o - 0.2
            c = o + 0.05
            v = 1.0 + i * 0.01
            data.append([ts, o, h, l, c, v])
        return data


@pytest.mark.asyncio
async def test_get_ohlcv_cache_returns_cached_data(monkeypatch):
    loader = BinanceDataLoader()
    loader.mock = False
    loader.exchange = FakeExchange()

    # Disable rate limiter delay
    async def no_wait():
        return None
    loader.rate_limiter.wait_if_needed = no_wait

    data1 = await loader.get_ohlcv("AAA/USDT", timeframe="1h", limit=50, use_cache=True)
    data2 = await loader.get_ohlcv("AAA/USDT", timeframe="1h", limit=50, use_cache=True)

    assert isinstance(data1, list) and isinstance(data2, list)
    assert loader.exchange.calls == 1
    assert data1 == data2
