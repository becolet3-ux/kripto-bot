import ccxt.async_support as ccxt
import asyncio
from config.settings import settings

async def try_connect(exchange_id, name, options=None):
    print(f"\n🔍 Testing {name}...")
    exchange = None
    try:
        config = {
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
        }
        if options:
            config.update(options)
            
        if not hasattr(ccxt, exchange_id):
            print(f"⚠️ Skipped: {exchange_id} not supported in this CCXT version.")
            return False

        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class(config)
        
        # Try to fetch balance (requires valid keys)
        balance = await exchange.fetch_balance()
        print(f"✅ SUCCESS! This key belongs to {name}.")
        await exchange.close()
        return True
    except Exception as e:
        error_msg = str(e)
        if "Invalid Api-Key ID" in error_msg:
            print(f"❌ Failed: Invalid Key for {name}")
        elif "Signature for this request is not valid" in error_msg:
             print(f"⚠️ Key Exists but Secret is WRONG for {name}")
        else:
            print(f"❌ Failed ({name}): {error_msg}")
        
        if exchange:
            await exchange.close()
        return False

async def main():
    print("--- API Key Detective ---")
    print(f"Checking Key: {settings.BINANCE_API_KEY[:4]}...{settings.BINANCE_API_KEY[-4:]}")
    
    # 1. Binance Global (Spot)
    if await try_connect('binance', 'Binance Global (Spot)'): return

    # 2. Binance Global (Futures)
    if await try_connect('binance', 'Binance Global (Futures)', {'options': {'defaultType': 'future'}}): return

    # 3. Binance TR
    # Binance TR is often 'binancetr' or 'trbinance'
    if 'binancetr' in ccxt.exchanges:
        if await try_connect('binancetr', 'Binance TR'): return
    else:
        print("\n⚠️ Skipping Binance TR (driver not found)")

    # 4. Binance Testnet (Spot)
    print("\n🔍 Testing Binance Testnet (Spot)...")
    exchange = None
    try:
        exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
        })
        exchange.set_sandbox_mode(True) # Enable Testnet
        await exchange.fetch_balance()
        print(f"✅ SUCCESS! This key belongs to Binance Testnet.")
        await exchange.close()
        return
    except Exception as e:
        print(f"❌ Failed (Testnet): {e}")
        if exchange:
            await exchange.close()
        
    print("\n⚠️ RESULT: This key does not seem to work on any known Binance platform.")

if __name__ == "__main__":
    asyncio.run(main())
