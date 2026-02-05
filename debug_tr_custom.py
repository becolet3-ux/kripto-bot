import asyncio
from src.collectors.binance_tr_client import BinanceTRClient
from config.settings import settings

async def main():
    print("--- Binance TR Custom Client Test ---")
    
    client = BinanceTRClient()
    
    try:
        # 1. Test Public Time
        print("\n1. Testing Server Time...")
        time_resp = await client.get_time()
        print(f"✅ Time: {time_resp}")

        # 2. Test Account Info (Signed)
        print("\n2. Testing Account Balance (Signed)...")
        account_resp = await client.get_account_info()
        
        if account_resp.get('code') == 0:
            print("✅ Login SUCCESS!")
            data = account_resp.get('data', {})
            assets = data.get('accountAssets', [])
            
            # Filter non-zero assets
            my_assets = [a for a in assets if float(a.get('free', 0)) > 0 or float(a.get('locked', 0)) > 0]
            print(f"💰 Your Assets: {my_assets}")
        else:
            print(f"❌ Login Failed: {account_resp}")

        # 3. Test Symbols
        # print("\n3. Fetching Symbols...")
        # symbols_resp = await client.get_symbols()
        # print(f"✅ Symbols Fetched: {len(symbols_resp.get('data', {}).get('list', []))} pairs found.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
