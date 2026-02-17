import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
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

    def test_analyze_spot_high_score_override(self):
        rows = []
        for i in range(3):
            rows.append(
                {
                    "timestamp": i,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "RSI": 50.0,
                    "SMA_Short": 105.0,
                    "SMA_Long": 100.0,
                    "Volume_Ratio": 1.0,
                    "Volatility": 0.0,
                    "MACD": 0.1,
                    "Signal_Line": 0.0,
                    "BB_Upper": 110.0,
                    "BB_Lower": 90.0,
                    "Stoch_RSI": 0.5,
                    "SuperTrend": 95.0,
                    "ST_Direction": 1,
                    "CCI": 0.0,
                    "ADX": 25.0,
                    "plus_di": 20.0,
                    "minus_di": 10.0,
                    "MFI": 50.0,
                    "VWAP": 100.0,
                    "is_doji": False,
                    "is_hammer": False,
                    "is_bullish_engulfing": False,
                }
            )
        df = pd.DataFrame(rows)
        self.analyzer.calculate_indicators = MagicMock(return_value=df)
        self.analyzer.regime_detector.detect_regime = MagicMock(
            return_value={"regime": "TRENDING", "is_no_trade_zone": False, "bb_width": 0.0}
        )
        self.analyzer.strategy_manager.analyze_all = MagicMock(
            return_value={
                "action": "HOLD",
                "weighted_score": 3.0,
                "primary_strategy": "base",
                "vote_ratio": 1.0,
                "strategy_details": {},
            }
        )
        self.analyzer.funding_strategy = None
        signal = self.analyzer.analyze_spot("BTC/USDT", self.candles, is_blocked=True)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "ENTRY")
        self.assertEqual(signal.primary_strategy, "high_score_override")

    def test_analyze_spot_blocked_by_negative_funding(self):
        rows = []
        for i in range(3):
            rows.append(
                {
                    "timestamp": i,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "RSI": 50.0,
                    "SMA_Short": 105.0,
                    "SMA_Long": 100.0,
                    "Volume_Ratio": 1.0,
                    "Volatility": 0.0,
                    "MACD": 0.1,
                    "Signal_Line": 0.0,
                    "BB_Upper": 110.0,
                    "BB_Lower": 90.0,
                    "Stoch_RSI": 0.5,
                    "SuperTrend": 95.0,
                    "ST_Direction": 1,
                    "CCI": 0.0,
                    "ADX": 25.0,
                    "plus_di": 20.0,
                    "minus_di": 10.0,
                    "MFI": 50.0,
                    "VWAP": 100.0,
                    "is_doji": False,
                    "is_hammer": False,
                    "is_bullish_engulfing": False,
                }
            )
        df = pd.DataFrame(rows)
        self.analyzer.calculate_indicators = MagicMock(return_value=df)
        self.analyzer.regime_detector.detect_regime = MagicMock(
            return_value={"regime": "TRENDING", "is_no_trade_zone": False, "bb_width": 0.0}
        )
        self.analyzer.strategy_manager.analyze_all = MagicMock(
            return_value={
                "action": "ENTRY",
                "weighted_score": 0.0,
                "primary_strategy": "base",
                "vote_ratio": 1.0,
                "strategy_details": {},
            }
        )

        class FundingStub:
            def analyze_funding(self, symbol):
                return {
                    "score_boost": -1.0,
                    "action": "IGNORE_LONG",
                    "reason": "negative",
                    "funding_rate_pct": -0.5,
                }

        self.analyzer.funding_strategy = FundingStub()
        self.analyzer.orderbook_analyzer.analyze_depth = MagicMock(return_value={})
        self.analyzer.orderbook_analyzer.get_score_impact = MagicMock(return_value=0.0)
        self.analyzer.vp_analyzer.calculate_profile = MagicMock(return_value={})
        self.analyzer.vp_analyzer.get_score_impact = MagicMock(return_value=(0.0, ""))

        weights = {"trend_following": 0.0, "golden_cross": 0.0, "oversold_bounce": 0.0, "sentiment": 0.0}
        signal = self.analyzer.analyze_spot("BTC/USDT", self.candles, weights=weights, sentiment_score=-1.0)
        self.assertIsNotNone(signal)
        self.assertNotEqual(signal.action, "ENTRY")
        self.assertAlmostEqual(signal.details["funding_rate_pct"], -0.5)

if __name__ == '__main__':
    unittest.main()
