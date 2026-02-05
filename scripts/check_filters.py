
from src.collectors.binance_tr_client import BinanceTRClient
import json

def check_filters():
    client = BinanceTRClient()
    print("Fetching exchange info...")
    resp = client.get_symbols()
    
    if resp.get('code') != 0:
        print(f"Error: {resp}")
        return

    symbols = resp.get('data', {}).get('list', [])
    targets = ['ZK_TRY', 'FOGO_TRY', 'BTC_TRY']
    
    for t in targets:
        print(f"\n--- {t} ---")
        found = next((s for s in symbols if s['symbol'] == t), None)
        if found:
            filters = found.get('filters', [])
            for f in filters:
                if f['filterType'] in ['LOT_SIZE', 'MARKET_LOT_SIZE', 'NOTIONAL', 'MIN_NOTIONAL']:
                    print(f"   {f['filterType']}: {f}")
            
            # Check precision fields
            print(f"   basePrecision: {found.get('basePrecision')}")
            print(f"   quotePrecision: {found.get('quotePrecision')}")
        else:
            print("   Symbol not found.")

if __name__ == "__main__":
    check_filters()
