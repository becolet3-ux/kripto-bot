import ccxt.async_support as ccxt
import asyncio
from config.settings import settings

async def test_login():
    print("--- Binance Bağlantı Testi ---")
    
    # 1. Spot Bağlantısını Test Et
    print("\n1. Spot API Test Ediliyor...")
    try:
        spot = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
        })
        balance = await spot.fetch_balance()
        print("✅ Spot Bağlantısı BAŞARILI!")
        await spot.close()
    except Exception as e:
        print(f"❌ Spot Bağlantı Hatası: {e}")
        # Hata detayını yazdır
        if hasattr(e, 'args'):
            print(f"   Detay: {e.args}")

    # 2. Vadeli (Futures) Bağlantısını Test Et
    print("\n2. Futures (Vadeli) API Test Ediliyor...")
    try:
        futures = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_SECRET_KEY,
            'options': {'defaultType': 'future'}
        })
        balance = await futures.fetch_balance()
        print("✅ Futures Bağlantısı BAŞARILI!")
        await futures.close()
    except Exception as e:
        print(f"❌ Futures Bağlantı Hatası: {e}")

if __name__ == "__main__":
    asyncio.run(test_login())
