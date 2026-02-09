import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.multi_timeframe import analyze_single_timeframe

class MockExchange:
    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        # Generate 100 candles
        dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=timeframe)
        
        # Base Price
        base_price = 100.0
        
        # Trend
        if symbol == 'BULLISH':
            trend = np.linspace(0, 20, limit) # Strong Up
        elif symbol == 'BEARISH':
            trend = np.linspace(0, -20, limit) # Strong Down
        else:
            trend = np.sin(np.linspace(0, 10, limit)) * 2 # Ranging
            
        # Random noise
        noise = np.random.normal(0, 0.5, limit)
        
        close = base_price + trend + noise
        open_p = close - np.random.normal(0, 0.2, limit)
        high = np.maximum(open_p, close) + abs(np.random.normal(0, 0.5, limit))
        low = np.minimum(open_p, close) - abs(np.random.normal(0, 0.5, limit))
        volume = np.random.randint(100, 1000, limit)
        
        data = []
        for i in range(limit):
            data.append([
                dates[i].value // 10**6,
                open_p[i],
                high[i],
                low[i],
                close[i],
                volume[i]
            ])
            
        return data

def test_analyze_single_timeframe():
    exchange = MockExchange()
    
    print("--- Testing analyze_single_timeframe ---")
    
    # Test Bullish
    print("\n1. Testing BULLISH Data:")
    res = analyze_single_timeframe('BULLISH', '1h', exchange)
    print(res)
    if res['direction'] == 'LONG':
        print("✅ Correctly identified LONG")
    else:
        print(f"❌ Failed to identify LONG (Got {res['direction']})")
        
    # Test Bearish
    print("\n2. Testing BEARISH Data:")
    res = analyze_single_timeframe('BEARISH', '1h', exchange)
    print(res)
    if res['direction'] == 'SHORT':
        print("✅ Correctly identified SHORT")
    else:
        print(f"❌ Failed to identify SHORT (Got {res['direction']})")
        
    # Test Ranging
    print("\n3. Testing RANGING Data:")
    res = analyze_single_timeframe('RANGING', '1h', exchange)
    print(res)
    if res['direction'] == 'NEUTRAL':
        print("✅ Correctly identified NEUTRAL")
    else:
        print(f"❌ Failed to identify NEUTRAL (Got {res['direction']})")

if __name__ == "__main__":
    test_analyze_single_timeframe()
