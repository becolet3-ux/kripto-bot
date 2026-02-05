import requests
import time
import hashlib
import hmac
import urllib.parse
import json

# Try different base URLs
URLS = [
    "https://www.binance.tr",
    "https://api.binance.tr",
    "https://api.trbinance.com"
]

def test_url(base_url):
    print(f"\nTesting Base URL: {base_url}")
    try:
        # Test 1: Public Time
        endpoint = "/open/v1/common/time"
        url = f"{base_url}{endpoint}"
        print(f"GET {url}")
        resp = requests.get(url, verify=False, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Response: {resp.json()}")
        else:
            print(f"Error: {resp.text}")

        # Test 2: Public Symbols (if time worked)
        if resp.status_code == 200:
            endpoint = "/open/v1/common/symbols"
            url = f"{base_url}{endpoint}"
            print(f"GET {url}")
            resp = requests.get(url, verify=False, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                symbols = data.get('data', {}).get('list', [])
                print(f"Found {len(symbols)} symbols.")
                
                # Check for BTC_USDT
                found_btc_usdt = any(s['symbol'] == 'BTC_USDT' for s in symbols)
                found_btcusdt = any(s['symbol'] == 'BTCUSDT' for s in symbols)
                print(f"BTC_USDT found: {found_btc_usdt}")
                print(f"BTCUSDT found: {found_btcusdt}")
                
                # Check USDT pairs count
                usdt_pairs = [s['symbol'] for s in symbols if 'USDT' in s['symbol']]
                print(f"USDT pairs count: {len(usdt_pairs)}")
                if usdt_pairs:
                    print(f"Sample USDT pairs: {usdt_pairs[:5]}")
            else:
                print(f"Symbols Error: {resp.text}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    
    for url in URLS:
        test_url(url)
