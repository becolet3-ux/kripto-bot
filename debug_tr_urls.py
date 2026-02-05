import ccxt.async_support as ccxt
import asyncio
from config.settings import settings

async def try_tr_url(url_base):
    print(f"\nTesting URL: {url_base}")
    
    exchange = ccxt.binance({
        'apiKey': settings.BINANCE_API_KEY,
        'secret': settings.BINANCE_SECRET_KEY,
        'urls': {
            'api': {
                'public': url_base,
                'private': url_base,
            },
        }
    })
    
    try:
        # 1. Try public request first (ping)
        # We need to access a public endpoint. fetch_time is good.
        try:
            time = await exchange.fetch_time()
            print(f"✅ Public API Access OK! Server Time: {time}")
        except Exception as e:
            print(f"❌ Public API Failed: {e}")
            await exchange.close()
            return

        # 2. Try private request (balance)
        balance = await exchange.fetch_balance()
        print(f"✅✅ SUCCESS! Private API Access OK with {url_base}")
        print(f"Balance: {list(balance.keys())[:3]}")
        await exchange.close()
        return True

    except Exception as e:
        print(f"❌ Private API Failed: {e}")
        await exchange.close()
        return False

async def main():
    print("--- Binance TR URL Hunter ---")
    
    # List of potential Binance TR API URLs
    urls = [
        'https://www.trbinance.com/api', # Common
        'https://api.trbinance.com/api',
        'https://www.binance.tr/api',
        'https://api.binance.me/api', # Sometimes used for TR?
        'https://www.trbinance.com', # Without /api suffix?
        'https://api.trbinance.com',
    ]
    
    for url in urls:
        if await try_tr_url(url):
            print(f"\n🎉 FOUND IT! The correct URL is: {url}")
            break

if __name__ == "__main__":
    asyncio.run(main())
