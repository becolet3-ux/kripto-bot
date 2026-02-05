import asyncio
from config.settings import settings

async def main():
    print("--- Binance TR Final Check ---")
    
    # 1. Direct Import Attempt
    try:
        from ccxt.async_support import binancetr
        print("✅ SUCCESS: Imported binancetr directly!")
        
        exchange = binancetr({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
        })
        
        try:
            print("Testing connection with binancetr driver...")
            balance = await exchange.fetch_balance()
            print("✅✅ CONNECTED TO BINANCE TR!")
            print(f"Balance: {list(balance.keys())[:3]}")
        except Exception as e:
            print(f"❌ Connection Failed: {e}")
        finally:
            await exchange.close()
            
    except ImportError:
        print("❌ Failed to import binancetr directly.")
        
        # 2. Try 'binance' driver with api.binance.me
        print("\nTrying generic 'binance' driver with api.binance.me...")
        import ccxt.async_support as ccxt
        exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
            'urls': {
                'api': {
                    'public': 'https://api.binance.me/api/v3',
                    'private': 'https://api.binance.me/api/v3',
                }
            }
        })
        try:
            balance = await exchange.fetch_balance()
            print("✅✅ CONNECTED via api.binance.me!")
        except Exception as e:
            print(f"❌ api.binance.me Failed: {e}")
        finally:
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
