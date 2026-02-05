import ccxt.async_support as ccxt
import asyncio
from config.settings import settings

async def try_connect(exchange_id, name, options=None, sandbox=False):
    print(f"\n🔍 Testing {name}...")
    exchange = None
    try:
        config = {
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
        }
        if options:
            config.update(options)
            
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class(config)
        
        if sandbox:
            exchange.set_sandbox_mode(True)
        
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
    print("--- API Key Detective (Round 2) ---")
    
    # 1. Binance Futures Testnet
    # Note: explicit sandbox mode for futures
    if await try_connect('binance', 'Binance Futures Testnet', {'options': {'defaultType': 'future'}}, sandbox=True): return

    # 2. Binance US
    if hasattr(ccxt, 'binanceus'):
        if await try_connect('binanceus', 'Binance US'): return
    
    print("\n⚠️ Still no luck. The key might be deleted, inactive, or IP restricted.")

if __name__ == "__main__":
    asyncio.run(main())
