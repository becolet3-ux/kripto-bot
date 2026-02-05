
from src.collectors.binance_tr_client import BinanceTRClient
import sys

def test_top_symbols():
    client = BinanceTRClient()
    print("Fetching Top 100 Symbols...")
    try:
        symbols = client.get_top_symbols(limit=100)
        print(f"Result Count: {len(symbols)}")
        if len(symbols) > 0:
            print("Top 5:", symbols[:5])
            print("Bottom 5:", symbols[-5:])
            
        # Verify format
        for s in symbols:
            if not s.endswith('_TRY'):
                print(f"❌ Invalid symbol format: {s}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_top_symbols()
