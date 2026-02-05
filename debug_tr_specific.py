import ccxt
import ccxt.async_support as ccxt_async
import asyncio
from config.settings import settings

async def main():
    print("--- Binance TR Check ---")
    
    # 1. Check availability
    print(f"Is 'binancetr' in ccxt exchanges? {'yes' if 'binancetr' in ccxt.exchanges else 'no'}")
    
    # 2. Try to instantiate
    try:
        # Try async first
        if hasattr(ccxt_async, 'binancetr'):
            exchange = ccxt_async.binancetr({
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
            })
            print("Using ccxt.async_support.binancetr")
        else:
            # Fallback to generic binance with TR URLs if binancetr class is missing
            print("binancetr class not found, trying generic binance with TR URLs...")
            exchange = ccxt_async.binance({
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
                'urls': {
                    'api': {
                        'public': 'https://www.trbinance.com/apiv1', # TR often uses different endpoints
                        'private': 'https://www.trbinance.com/apiv1',
                    }
                }
            })
            # Note: Binance TR API is a bit different, often incompatible with standard Binance CCXT driver directly without proper mapping.
            # Best is to use 'binancetr' driver if available.
            
            # Let's check if we can import it dynamically
            import importlib
            try:
                # CCXT structure: ccxt.async_support.binancetr
                # If not exposed in top level, maybe valid exchange id
                pass
            except:
                pass

        # If we found a way to instantiate:
        print("Testing connection...")
        try:
            # Binance TR usually supports standard fetch_balance
            balance = await exchange.fetch_balance()
            print("✅ SUCCESS! Connected to Binance TR.")
            print(f"Balance keys: {list(balance.keys())[:5]}")
        except Exception as e:
            print(f"❌ Connection Failed: {e}")
        finally:
            await exchange.close()

    except Exception as e:
        print(f"❌ Setup Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
