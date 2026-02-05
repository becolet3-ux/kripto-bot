import ccxt.async_support as ccxt
import asyncio
from config.settings import settings

async def main():
    print("--- Manual Futures Testnet Check ---")
    
    exchange = ccxt.binance({
        'apiKey': settings.BINANCE_API_KEY,
        'secret': settings.BINANCE_SECRET_KEY,
        'options': {'defaultType': 'future'},
        'urls': {
            'api': {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
            },
        }
    })
    
    # Manually override to force testnet URL usage for fetch_balance
    # CCXT might be tricky with this, so let's try a direct request via the exchange object if possible,
    # or just trust the url override if it works.
    # Actually, CCXT 'urls' override is the standard way.
    
    # We need to map the endpoints correctly.
    # For binance, 'fapiPublic' and 'fapiPrivate' might be the keys for futures.
    
    exchange.urls['api']['fapiPublic'] = 'https://testnet.binancefuture.com/fapi/v1'
    exchange.urls['api']['fapiPrivate'] = 'https://testnet.binancefuture.com/fapi/v1'
    
    print("Testing connection to https://testnet.binancefuture.com ...")
    try:
        # fetch_balance on futures uses /fapi/v2/balance or similar
        # We'll see if this works.
        balance = await exchange.fetch_balance()
        print(f"✅ SUCCESS! This is a Futures Testnet Key.")
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
