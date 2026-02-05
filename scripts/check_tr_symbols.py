from src.collectors.binance_tr_client import BinanceTRClient
import sys
import os

import time

# Add project root to path
sys.path.append(os.getcwd())

def check_symbols():
    client = BinanceTRClient()
    
    # Try BTC_TRY
    print("Testing BTC_TRY with limit=100 (1m)...")
    resp = client.get_klines("BTC_TRY", interval='1m', limit=100)
    if resp.get('code') == 0:
        print("✅ BTC_TRY exists.")
        data = resp.get('data')
        klines = data if isinstance(data, list) else data.get('list', [])
        print(f"Klines count: {len(klines)}")
        if len(klines) > 0:
            print(f"First kline: {klines[0]}")
    else:
        print(f"❌ BTC_TRY failed: {resp}")

    print("Testing Price...")
    try:
        price = client.get_ticker_price("BTC_TRY")
        print(f"BTC_TRY Price: {price}")
    except Exception as e:
        print(f"Price check failed: {e}")
        
    time.sleep(1)

    # Try BTCUSDT
    print("Testing BTCUSDT...")
    resp = client.get_klines("BTCUSDT", limit=1)
    if resp.get('code') == 0:
        print("✅ BTCUSDT exists.")
    else:
        print(f"❌ BTCUSDT failed: {resp}")

    time.sleep(1)
    
    # Try BTC_USDT
    print("Testing BTC_USDT...")
    resp = client.get_klines("BTC_USDT", limit=1)
    if resp.get('code') == 0:
        print("✅ BTC_USDT exists.")
    else:
        print(f"❌ BTC_USDT failed: {resp}")
        
    print("\nFetching Binance TR Symbols...")
    resp = client.get_symbols()
    
    if resp.get('code') == 0:
        symbols = resp.get('data', {}).get('list', [])
        print(f"✅ Found {len(symbols)} symbols on Binance TR.")
        
        tr_symbols = [s['symbol'] for s in symbols]
        
        suffixes = set()
        for s in tr_symbols:
            if '_' in s:
                suffixes.add(s.split('_')[1])
        
        print(f"Available Quote Currencies: {suffixes}")

        usdt_pairs = [s for s in tr_symbols if 'USDT' in s]
        print(f"Found {len(usdt_pairs)} USDT pairs.")
        print("First 10 USDT pairs:", usdt_pairs[:10])
        
        check_list = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'AVAX_USDT', 'PEPE_USDT']
        for s in check_list:
            status = "✅" if s in tr_symbols else "❌"
            print(f"{status} {s}")
            
    else:
        print(f"❌ Failed to fetch symbols: {resp}")

if __name__ == "__main__":
    check_symbols()
