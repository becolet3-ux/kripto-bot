import pandas as pd
import numpy as np
import talib as ta
from typing import Dict, Any, List
from src.strategies.strategy_manager import StrategyManager

# Mock Strategy to force ENTRY
class MockStrategy:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight
        
    def analyze(self, df):
        return {
            "strategy": self.name,
            "action": "ENTRY",
            "score": 10.0,
            "details": {"mock": True}
        }

class MockStrategyManager(StrategyManager):
    def __init__(self):
        super().__init__()
        # Override strategies to force consensus
        self.strategies = [
            MockStrategy("MOCK_BREAKOUT", 0.4),
            MockStrategy("MOCK_MOMENTUM", 0.3),
            MockStrategy("MOCK_MEANREV", 0.3)
        ]

# Mock Exchange for MTF Data
class MockExchange:
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List[List]:
        # Generate dummy OHLCV data that looks Bullish (for Consensus)
        # 15m: Bullish
        # 1h: Bullish
        # 4h: Bullish
        
        # CCXT Format: [timestamp, open, high, low, close, volume]
        dates = pd.date_range(end='2024-01-01', periods=limit, freq=timeframe)
        timestamps = dates.astype(np.int64) // 10**6
        
        closes = np.linspace(100, 110, limit)
        opens = np.linspace(99, 109, limit)
        highs = closes + 1
        lows = opens - 1
        volumes = np.random.randint(1000, 5000, limit)
        
        data = []
        for i in range(limit):
            data.append([
                timestamps[i],
                opens[i],
                highs[i],
                lows[i],
                closes[i],
                float(volumes[i])
            ])
        return data

def calculate_indicators(df):
    # Bollinger Bands
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = ta.BBANDS(df['close'], timeperiod=20)
    
    # RSI
    df['RSI'] = ta.RSI(df['close'], timeperiod=14)
    
    # MACD
    df['MACD'], df['Signal_Line'], df['MACD_Hist'] = ta.MACD(df['close'])
    
    # ADX
    df['ADX'] = ta.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    
    # Volume Ratio (Vol / SMA20 Vol)
    vol_sma = ta.SMA(df['volume'].astype(float), timeperiod=20)
    df['Volume_Ratio'] = df['volume'] / vol_sma
    
    # SuperTrend (Simplified for test)
    # ATR
    df['ATR'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=10)
    # Mock SuperTrend Direction (1 = Bullish, -1 = Bearish)
    # Let's say if Close > SMA50 it's Bullish
    sma50 = ta.SMA(df['close'], timeperiod=50)
    df['ST_Direction'] = np.where(df['close'] > sma50, 1, -1)
    
    return df

def run_test():
    print("🚀 Starting Quick MTF Test (Forced ENTRY + Mock Exchange)...")
    
    # 1. Initialize Mock Exchange
    exchange = MockExchange()
    print(f"✅ Mock Exchange Initialized")

    # 2. Initialize Strategy Manager (MOCK)
    sm = MockStrategyManager()
    print("✅ MockStrategyManager Initialized (Will force ENTRY)")
    
    # 3. Create Dummy Data
    print("📊 Generating Dummy Data (100 candles)...")
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    data = {
        'timestamp': dates,
        'open': np.linspace(100, 110, 100),
        'high': np.linspace(101, 111, 100),
        'low': np.linspace(99, 109, 100),
        'close': np.linspace(100, 110, 100), 
        'volume': np.random.randint(1000, 5000, 100)
    }
    df = pd.DataFrame(data)
    
    # Add volatility
    df['close'] = df['close'] + np.random.normal(0, 0.5, 100)
    df['high'] = df['close'] + 0.5
    df['low'] = df['close'] - 0.5
    
    # Ensure float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate Indicators needed by sub-strategies
    print("🧮 Calculating Indicators...")
    df = calculate_indicators(df)
    
    # Fill NaN
    df.fillna(0, inplace=True)

    # 4. Run Analysis
    print("🔍 Running analyze_all()...")
    symbol = 'BTC/USDT'
    
    try:
        result = sm.analyze_all(df, symbol, exchange)
        
        print("\n📈 RESULT:")
        print(f"Action: {result['action']}")
        print(f"Score: {result['weighted_score']:.2f}")
        print(f"Vote Ratio: {result['vote_ratio']:.2f}")
        print(f"Primary Strategy: {result['primary_strategy']}")
        
        if 'mtf_analysis' in result['strategy_details']:
            print("\n🧩 MTF Details:")
            mtf = result['strategy_details']['mtf_analysis']
            print(f"Consensus: {mtf.get('consensus')}")
            print(f"Multiplier: {mtf.get('confidence_multiplier')}")
            print(f"Blocking Reason: {mtf.get('blocking_reason')}")
            
            # Print Timeframe details if available
            if 'timeframes' in mtf:
                print("\n   Timeframe Breakdown:")
                for tf, res in mtf['timeframes'].items():
                    print(f"   - {tf}: {res.get('direction')} (Confidence: {res.get('confidence'):.2f})")
        else:
            print("\n⚠️ MTF Analysis did not run (Action was likely HOLD)")
            
        print("\n✅ Test Completed Successfully")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
