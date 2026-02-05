import asyncio
import aiohttp
import ssl

async def test_direct_connection():
    url = "https://api.binance.com/api/v3/ping"
    print(f"Testing connection to {url}...")

    # 1. Normal Connection
    print("\n1. Normal Bağlantı Deneniyor...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"✅ Başarılı! Status: {response.status}")
                print(f"   Response: {await response.text()}")
    except Exception as e:
        print(f"❌ Normal Bağlantı Hatası: {e}")

    # 2. SSL Disabled Connection
    print("\n2. SSL Korumasız (Verify=False) Bağlantı Deneniyor...")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(url) as response:
                print(f"✅ SSL'siz Bağlantı BAŞARILI! Status: {response.status}")
                print(f"   Response: {await response.text()}")
    except Exception as e:
        print(f"❌ SSL'siz Bağlantı Hatası: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_connection())
