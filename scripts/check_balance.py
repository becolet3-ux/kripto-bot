from src.collectors.binance_tr_client import BinanceTRClient
from config.settings import settings
import json

def check_balance():
    print(f"Checking balance with API Key: {settings.BINANCE_API_KEY[:4]}...***")
    client = BinanceTRClient()
    
    try:
        # Check Time (Connectivity)
        time_resp = client.get_time()
        print(f"✅ Connection Successful (Server Time: {time_resp.get('serverTime')})")
        
        # Check Balance
        print("Fetching account info...")
        account_info = client.get_account_info()
        
        if account_info.get('code') == 0:
            print("\n💰 Balances:")
            assets = account_info.get('data', {}).get('accountAssets', [])
            has_funds = False
            for asset in assets:
                free = float(asset.get('free', 0))
                locked = float(asset.get('locked', 0))
                if free > 0 or locked > 0:
                    print(f"   - {asset.get('asset')}: {free} (Free) | {locked} (Locked)")
                    has_funds = True
            
            if not has_funds:
                print("   ⚠️ No funds found in the account.")
            else:
                print("\n✅ Account is ready for trading!")
        else:
            print(f"❌ Failed to fetch account info: {account_info}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_balance()
