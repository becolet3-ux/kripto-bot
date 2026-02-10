import asyncio
import aiohttp
import json

async def test_bapi():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    endpoints = [
        # Trending / Hot Symbols
        ("Hot Symbols", "https://www.binance.com/bapi/composite/v1/public/marketing/symbol/list"),
        # Futures Long/Short Ratio (Official API)
        ("L/S Ratio", "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"),
        # Square/Feed Popular (Guessing/Common unofficial)
        ("Feed Trending", "https://www.binance.com/bapi/feed/v1/public/feed/search/popular"),
        # Simple Ticker 24h
        ("Ticker 24h", "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT")
    ]

    async with aiohttp.ClientSession(headers=headers) as session:
        for name, url in endpoints:
            try:
                print(f"Testing {name}...")
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ {name}: Success")
                        # Print snippet
                        print(str(data)[:200])
                    else:
                        print(f"❌ {name}: Failed ({response.status})")
            except Exception as e:
                print(f"⚠️ {name}: Error ({e})")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_bapi())
