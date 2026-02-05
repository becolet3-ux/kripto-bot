from src.collectors.binance_tr_client import BinanceTRClient
from config.settings import settings
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

def check_balance():
    # Force TR client usage
    settings.IS_TR_BINANCE = True
    
    client = BinanceTRClient()
    print("Fetching Binance TR Account Info...")
    resp = client.get_account_info()
    
    if resp.get('code') == 0:
        print("Raw response keys:", resp.keys())
        print("Raw data:", resp.get('data')) 
        balances = resp.get('data', {}).get('balances', [])
        print(f"Balances count: {len(balances)}")
        
        for b in balances:
            free = float(b.get('free', 0))
            locked = float(b.get('locked', 0))
            if free > 0 or locked > 0:
                print(f"- {b['asset']}: Free={free}, Locked={locked}")
    else:
        print(f"❌ Failed to fetch account: {resp}")

if __name__ == "__main__":
    check_balance()
