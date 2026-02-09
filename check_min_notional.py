
import ccxt
import json

def check_filters():
    exchange = ccxt.binance()
    exchange.load_markets()
    
    symbols = ['D/USDT', 'KNC/USDT', 'SFP/USDT', 'BTC/USDT']
    
    for sym in symbols:
        if sym in exchange.markets:
            market = exchange.markets[sym]
            print(f"\n=== {sym} ===")
            print(f"Limits: {json.dumps(market['limits'], indent=2)}")
            # Specifically check min cost
            min_cost = market['limits']['cost']['min']
            print(f"Min Cost (Notional): {min_cost}")
        else:
            print(f"\n{sym} not found in markets.")

if __name__ == "__main__":
    check_filters()
