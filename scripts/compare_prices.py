import requests
import time
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))
from config.settings import settings
from collectors.binance_tr_client import BinanceTRClient

def get_global_price(symbol):
    # Global uses BTCTRY format
    symbol_global = symbol.replace("_", "")
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_global}"
    try:
        resp = requests.get(url)
        data = resp.json()
        if 'price' in data:
            return float(data['price'])
        return None
    except:
        return None

def main():
    print("--- Fiyat Karşılaştırması (Global vs TR) ---")
    print(f"Zaman: {time.strftime('%H:%M:%S')}")
    print(f"{'Sembol':<10} | {'Global':<15} | {'TR':<15} | {'Fark (%)':<10}")
    print("-" * 60)
    
    # Initialize TR Client
    tr_client = BinanceTRClient()
    
    symbols = settings.SYMBOLS 
    
    for symbol in symbols:
        # 1. Get Global Price
        p_global = get_global_price(symbol)
        
        # 2. Get TR Price (Force TR Endpoint)
        p_tr = None
        try:
            # Use _request directly to bypass Global fallback in get_ticker_24hr
            # Endpoint: /open/v1/ticker/24hr
            resp = tr_client._request("GET", "/open/v1/ticker/24hr", params={"symbol": symbol})
            
            if resp.get('code') == 0:
                data = resp.get('data')
                if isinstance(data, list) and len(data) > 0:
                    p_tr = float(data[0]['lastPrice'])
                elif isinstance(data, dict):
                    p_tr = float(data.get('lastPrice', 0))
        except Exception as e:
            print(f"TR Error ({symbol}): {e}")

        # 3. Compare
        str_global = f"{p_global:.2f}" if p_global else "N/A"
        str_tr = f"{p_tr:.2f}" if p_tr else "N/A"
        
        diff_str = "-"
        if p_global and p_tr:
            diff = p_tr - p_global
            diff_pct = (diff / p_global) * 100
            diff_str = f"{diff_pct:+.4f}%"
            
        print(f"{symbol:<10} | {str_global:<15} | {str_tr:<15} | {diff_str}")
        
        time.sleep(1)

    tr_client.close()

if __name__ == "__main__":
    main()
