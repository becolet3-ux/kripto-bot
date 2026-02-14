import asyncio
import pytest
from src.collectors.funding_rate_loader import FundingRateLoader


class FakeExchange:
    def fetch_funding_rates(self):
        return {
            "BTC/USDT:USDT": {"fundingRate": 0.0005, "fundingTimestamp": 1700000000000},
            "ETH/USDT": {"fundingRate": -0.0002, "fundingTimestamp": 1700000000000},
        }


@pytest.mark.asyncio
async def test_update_and_get_funding_rate_mappings(monkeypatch):
    loader = FundingRateLoader()
    # Inject fake exchange
    loader.exchange = FakeExchange()
    # Force update regardless of interval
    loader.last_update_time = 0
    loader.update_interval = 0

    await loader.update_funding_rates()

    # Direct match with :USDT form
    assert loader.get_funding_rate("BTC/USDT:USDT") == 0.0005
    # Standard slash format should also resolve from :USDT key
    assert loader.get_funding_rate("BTC/USDT") == 0.0005
    # Underscore format resolution
    assert loader.get_funding_rate("BTC_USDT") == 0.0005

    # ETH simple mapping and underscore variant
    assert loader.get_funding_rate("ETH/USDT") == -0.0002
    assert loader.get_funding_rate("ETH_USDT") == -0.0002

    # Unknown returns 0.0
    assert loader.get_funding_rate("FOO/USDT") == 0.0


@pytest.mark.asyncio
async def test_update_interval_skip(monkeypatch):
    loader = FundingRateLoader()
    loader.exchange = FakeExchange()
    loader.update_interval = 999999  # Large to force skip
    # Pre-populate with a value
    loader.funding_rates["BTC/USDT:USDT"] = {"rate": 0.001, "funding_time": 0, "timestamp": 0}
    # Set last_update_time to now to trigger skip
    import time
    loader.last_update_time = time.time()

    await loader.update_funding_rates()
    # Value should remain unchanged due to interval skip
    assert loader.get_funding_rate("BTC/USDT") == 0.001
