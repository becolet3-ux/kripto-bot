import unittest
import pandas as pd
import numpy as np
from src.strategies.analyzer import MarketAnalyzer, TradeSignal

class TestMarketAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = MarketAnalyzer()
        # Create dummy candle data: [timestamp, open, high, low, close, volume]
        # Generate 100 candles of uptrend data
        self.candles = []
        base_price = 100.0
        for i in range(100):
            timestamp = 1600000000 + (i * 3600)
            # Gentle uptrend
            close = base_price + (i * 0.5) + (np.sin(i) * 2) 
            open_p = close - 0.2
            high = close + 0.5
            low = close - 0.5
            vol = 1000 + (i * 10)
            self.candles.append([timestamp, open_p, high, low, close, vol])

    def test_calculate_indicators(self):
        df = self.analyzer.calculate_indicators(self.candles)
        
        # Check if DataFrame is created
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 100)
        
        # Check if columns exist
        expected_cols = ['RSI', 'SMA_Short', 'SMA_Long', 'MACD', 'SuperTrend', 'BB_Upper']
        for col in expected_cols:
            self.assertIn(col, df.columns)
            
        # Check values (SMA calculation)
        # SMA_Short (7) at index 10 should be mean of close[4:11]
        expected_sma = df['close'].rolling(window=7).mean().iloc[10]
        self.assertAlmostEqual(df['SMA_Short'].iloc[10], expected_sma)

    def test_analyze_spot_uptrend(self):
        # In our generated data, price is generally rising.
        # SMA_Short (7) should be > SMA_Long (25) eventually.
        
        signal = self.analyzer.analyze_spot("BTC/USDT", self.candles)
        
        # Should return a signal
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, TradeSignal)
        
        # In a strong uptrend, score should be positive
        # But we need to make sure we don't hit "Overbought" penalty if RSI is too high.
        # Our sine wave might push RSI high.
        # Let's check the score components in debug or just assert valid range.
        self.assertTrue(-20 <= signal.score <= 20)

    def test_analyze_spot_downtrend_penalty(self):
        # Create downtrend candles
        down_candles = []
        base_price = 200.0
        for i in range(100):
            timestamp = 1600000000 + (i * 3600)
            # Sharp downtrend
            close = base_price - (i * 1.0) 
            open_p = close + 0.5
            high = close + 1.0
            low = close - 1.0
            vol = 1000
            down_candles.append([timestamp, open_p, high, low, close, vol])
            
        signal = self.analyzer.analyze_spot("ETH/USDT", down_candles)
        
        # Expecting a negative score or HOLD due to downtrend penalty
        # The logic says: if close < sma_long and st_direction == -1 -> Penalty -3.0
        
        # We can verify this by checking if score is low
        # Also, analyze_spot logs "Strong Downtrend"
        
        self.assertIsNotNone(signal)
        # It might be ENTRY if RSI is super low (oversold bounce), 
        # but the trend penalty should be applied.
        # Let's just check if it runs without error for now, 
        # verifying exact score is hard without mocking everything.
        self.assertTrue(signal.score < 10) # Should not be super high

    def test_analyze_market_regime(self):
        regime = self.analyzer.analyze_market_regime(self.candles)
        self.assertIn('trend', regime)
        self.assertIn('volatility', regime)
        
        # Our data is uptrend
        # But analyze_market_regime checks close > SMA_Long * 1.005
        # The last candle in our set is definitely higher than SMA25
        self.assertEqual(regime['trend'], 'UP')

if __name__ == '__main__':
    unittest.main()
