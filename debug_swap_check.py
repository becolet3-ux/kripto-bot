import ccxt.async_support as ccxt
import asyncio
from config.settings import settings

async def main():
    print("--- Swapped Key Check ---")
    
    # Try connecting with swapped keys
    # API = Secret, Secret = API
    api_key = settings.BINANCE_SECRET_KEY
    secret_key = settings.BINANCE_API_KEY
    
    print(f"Trying with SWAPPED keys...")
    print(f"API (was Secret): {api_key[:4]}...")
    print(f"Secret (was API): {secret_key[:4]}...")
    
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
        })
        balance = await exchange.fetch_balance()
        print(f"✅ SUCCESS! The keys were swapped!")
        await exchange.close()
    except Exception as e:
        print(f"❌ Failed even with swapped keys: {e}")
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
