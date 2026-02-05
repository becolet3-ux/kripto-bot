import ccxt
import ccxt.async_support as ccxt_async
import asyncio

def find_tr_exchange():
    print("--- Searching for Binance TR in CCXT ---")
    tr_exchanges = [x for x in ccxt.exchanges if 'tr' in x or 'turk' in x]
    print(f"Found TR-related exchanges: {tr_exchanges}")
    
    binance_related = [x for x in ccxt.exchanges if 'binance' in x]
    print(f"Found Binance-related exchanges: {binance_related}")

if __name__ == "__main__":
    find_tr_exchange()
