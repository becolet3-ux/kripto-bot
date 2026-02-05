import asyncio
import ccxt.async_support as ccxt_async
import ccxt as ccxt_sync
import time

async def test_async():
    print("--- Async Test Başlıyor ---")
    exchange = ccxt_async.binance({
        'enableRateLimit': True,
        'verify': False,  # SSL kapalı deniyoruz
        'timeout': 30000,
    })
    try:
        print("Async: Ticker çekiliyor...")
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Async Başarılı! BTC: {ticker['last']}")
    except Exception as e:
        print(f"❌ Async Hatası: {type(e).__name__} - {str(e)}")
    finally:
        await exchange.close()

def test_sync():
    print("\n--- Sync Test Başlıyor ---")
    exchange = ccxt_sync.binance({
        'enableRateLimit': True,
        'verify': False,
        'timeout': 30000,
    })
    try:
        print("Sync: Ticker çekiliyor...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Sync Başarılı! BTC: {ticker['last']}")
    except Exception as e:
        print(f"❌ Sync Hatası: {type(e).__name__} - {str(e)}")

if __name__ == "__main__":
    # Önce Sync (daha basit)
    test_sync()
    # Sonra Async
    asyncio.run(test_async())
