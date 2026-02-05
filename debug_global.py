
import asyncio
import ccxt.async_support as ccxt
from config.settings import settings
import os

async def test_global_connection():
    print("🌍 Testing Binance Global Connection...")
    print(f"🔑 API Key: {settings.BINANCE_API_KEY[:4]}...{settings.BINANCE_API_KEY[-4:] if settings.BINANCE_API_KEY else 'None'}")

    # 1. Test Futures Connection
    print("\n--- Testing Futures (USDT-M) ---")
    futures_exchange = ccxt.binance({
        'apiKey': settings.BINANCE_API_KEY,
        'secret': settings.BINANCE_SECRET_KEY,
        'options': {'defaultType': 'future'}
    })
    
    try:
        await futures_exchange.load_markets()
        print("✅ Futures Markets Loaded")
        
        # Fetch Funding Rate
        funding = await futures_exchange.fetch_funding_rate('BTC/USDT')
        print(f"💰 BTC/USDT Funding Rate: {funding['fundingRate']:.6f} (Next: {funding['fundingTimestamp']})")
        
        # Fetch Balance
        balance = await futures_exchange.fetch_balance()
        usdt_free = balance['free'].get('USDT', 0)
        print(f"wallet USDT (Futures) Free: {usdt_free}")
        
    except Exception as e:
        print(f"❌ Futures Error: {e}")
    finally:
        await futures_exchange.close()

    # 2. Test Spot Connection
    print("\n--- Testing Spot ---")
    spot_exchange = ccxt.binance({
        'apiKey': settings.BINANCE_API_KEY,
        'secret': settings.BINANCE_SECRET_KEY,
        'options': {'defaultType': 'spot'}
    })
    
    try:
        await spot_exchange.load_markets()
        print("✅ Spot Markets Loaded")
        
        # Fetch Balance
        balance = await spot_exchange.fetch_balance()
        usdt_free = balance['free'].get('USDT', 0)
        print(f"wallet USDT (Spot) Free: {usdt_free}")
        
    except Exception as e:
        print(f"❌ Spot Error: {e}")
    finally:
        await spot_exchange.close()

if __name__ == "__main__":
    asyncio.run(test_global_connection())
