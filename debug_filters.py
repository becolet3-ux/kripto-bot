
import requests
import json
import math

def get_symbol_filters(symbol):
    # Try Global API
    url_global = "https://api.binance.me/api/v3/exchangeInfo?symbol=" + symbol.replace('_', '')
    print(f"Fetching Global API for {symbol}...")
    try:
        r = requests.get(url_global)
        data = r.json()
        if 'symbols' in data and len(data['symbols']) > 0:
            s = data['symbols'][0]
            print(f"Global API Found {symbol}:")
            for f in s['filters']:
                if f['filterType'] in ['LOT_SIZE', 'MARKET_LOT_SIZE', 'NOTIONAL', 'MIN_NOTIONAL']:
                    print(f"  {f['filterType']}: {f}")
        else:
            print("Global API: Symbol not found.")
    except Exception as e:
        print(f"Global API Error: {e}")

    # Try TR API (public market data if available, or just common knowledge)
    # TR API public endpoint for exchange info?
    # https://www.binance.tr/open/v1/common/symbols exists?
    
    url_tr = "https://www.binance.tr/open/v1/common/symbols"
    print(f"\nFetching TR API for {symbol}...")
    try:
        r = requests.get(url_tr)
        data = r.json()
        if data['code'] == 0:
            found = False
            for s in data['data']['list']:
                if s['symbol'] == symbol:
                    found = True
                    print(f"TR API Found {symbol}:")
                    # TR API symbol info structure might be different
                    print(json.dumps(s, indent=2))
                    break
            if not found:
                print("TR API: Symbol not found in list.")
        else:
            print(f"TR API Error: {data}")
    except Exception as e:
        print(f"TR API Error: {e}")

if __name__ == "__main__":
    get_symbol_filters("BONK_TRY")
    get_symbol_filters("PEPE_TRY")
