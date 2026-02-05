from src.collectors.binance_tr_client import BinanceTRClient
import sys
import os

sys.path.append(os.getcwd())

def check_pairs():
    client = BinanceTRClient()
    target_pairs = ['BTC_TRY', 'ETH_TRY', 'SOL_TRY', 'AVAX_TRY', 'PEPE_TRY', 'USDT_TRY']
    
    print("Checking pairs availability on Binance TR...")
    for pair in target_pairs:
        resp = client.get_klines(pair, limit=1)
        if resp.get('code') == 0:
            print(f"✅ {pair} exists.")
        else:
            print(f"❌ {pair} failed: {resp}")

if __name__ == "__main__":
    check_pairs()
