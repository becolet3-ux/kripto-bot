import asyncio
import pytest
from src.collectors.binance_loader import BinanceDataLoader


@pytest.mark.asyncio
async def test_binance_loader_mock_price_and_funding():
    loader = BinanceDataLoader()
    assert loader.mock is True
    price = await loader.get_current_price("BTC/USDT")
    assert isinstance(price, (int, float))
    fr = await loader.get_funding_rate("BTC/USDT")
    assert fr["symbol"] == "BTC/USDT"
    assert "fundingRate" in fr


@pytest.mark.asyncio
async def test_binance_loader_mock_ohlcv():
    loader = BinanceDataLoader()
    data = await loader.get_ohlcv("ETH/USDT", timeframe="1h", limit=60)
    assert isinstance(data, list)
    assert len(data) == 60
    # Each entry should have at least 6 elements
    assert len(data[0]) >= 6
