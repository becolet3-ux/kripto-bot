import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath("src"))

from collectors.binance_tr_client import BinanceTRClient
from config.settings import settings

def main():
    print("--- Checking Live Ready Status ---")
    
    # 1. Initialize Client
    try:
        client = BinanceTRClient()
        print("✅ Client Initialized")
    except Exception as e:
        print(f"❌ Client Init Failed: {e}")
        return

    # 2. Check Balance
    print("\n--- Checking Balance ---")
    try:
        balance = client.fetch_balance()
        if 'free' in balance:
            print(f"✅ Balance Fetched: {balance['free']}")
            if balance['free'].get('USDT', 0) > 0 or balance['free'].get('TRY', 0) > 0:
                print("✅ Non-zero balance found.")
            else:
                print("⚠️ Zero balance (might be expected if funds not moved yet)")
        else:
            print(f"⚠️ Unexpected Balance Format: {balance}")
    except Exception as e:
        print(f"❌ Balance Check Failed: {e}")

    # 3. Check Market Data (Global API Fallback)
    print("\n--- Checking Market Data (BTC_TRY) ---")
    try:
        # Ticker
        ticker = client.get_ticker_24hr("BTC_TRY")
        if ticker.get('code') == 0:
            print(f"✅ Ticker 24hr (BTC_TRY): Success (Source: {ticker.get('data', {}).get('symbol', 'Unknown')})")
        else:
            print(f"❌ Ticker 24hr Failed: {ticker}")
            
        # Klines
        klines = client.get_klines("BTC_TRY", limit=5)
        if klines.get('code') == 0:
            data = klines.get('data')
            count = len(data) if isinstance(data, list) else len(data.get('list', []))
            print(f"✅ Klines (BTC_TRY): Success ({count} candles)")
        else:
             print(f"❌ Klines Failed: {klines}")
             
    except Exception as e:
        print(f"❌ Market Data Check Failed: {e}")

    # 4. Check USDT_TRY Price (for conversion)
    print("\n--- Checking USDT_TRY Price ---")
    try:
        price = client.get_ticker_price("USDT_TRY")
        print(f"✅ USDT_TRY Price: {price}")
        if price > 30:
            print("✅ Price looks reasonable (approx > 30 TRY)")
        else:
            print(f"⚠️ Price seems low? {price}")
    except Exception as e:
        print(f"❌ USDT_TRY Check Failed: {e}")

    client.close()
    print("\n--- Done ---")

if __name__ == "__main__":
    main()
