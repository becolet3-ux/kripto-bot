from typing import Dict, Any
import pandas as pd
import numpy as np

class MarketRegimeDetector:
    """
    Analyzes market regime (Trending vs Ranging) and identifies No-Trade Zones.
    Phase 3: Market Regime Detection
    """
    
    def __init__(self):
        pass

    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detects the current market regime based on indicators.
        Requires DF with: ADX, BB_Upper, BB_Lower, BB_Middle, RSI, VWAP, close
        """
        if df.empty or len(df) < 2:
            return {'regime': 'UNKNOWN', 'details': 'Insufficient data'}
            
        # Get latest and previous values
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Calculate Bollinger Band Width
        # Width = (Upper - Lower) / Middle
        curr_bb_width = (curr['BB_Upper'] - curr['BB_Lower']) / curr['BB_Middle'] if curr['BB_Middle'] > 0 else 0
        prev_bb_width = (prev['BB_Upper'] - prev['BB_Lower']) / prev['BB_Middle'] if prev['BB_Middle'] > 0 else 0
        
        bb_widening = curr_bb_width > prev_bb_width
        bb_narrow = curr_bb_width < 0.05 # Threshold for "narrow" (e.g., 5%) - tunable
        
        adx = curr.get('ADX', 0)
        
        regime = "NEUTRAL"
        
        # 1. Trending Detection
        if adx > 25 and bb_widening:
            regime = "TRENDING"
            
        # 2. Ranging Detection
        elif adx < 20 and bb_narrow:
            regime = "RANGING"
            
        # 3. No-Trade Zone Detection
        is_no_trade = self._check_no_trade_zone(df, curr, adx)
        
        return {
            'regime': regime,
            'is_no_trade_zone': is_no_trade,
            'adx': adx,
            'bb_width': curr_bb_width,
            'bb_widening': bb_widening
        }

    def _check_no_trade_zone(self, df: pd.DataFrame, curr: pd.Series, adx: float) -> bool:
        """
        Checks if the market is in a No-Trade Zone.
        Conditions:
        1. ADX < 20 (Weak Trend)
        2. RSI 40-60 (Indecisive Momentum)
        3. Price VWAP +/- 0.5% (Consolidation near fair value)
        4. Low Movement in last 4 hours (<1%)
        """
        # 1. ADX Check
        if adx >= 20:
            return False
            
        # 2. RSI Check
        rsi = curr.get('RSI', 50)
        if not (40 <= rsi <= 60):
            return False
            
        # 3. VWAP Check
        close = curr['close']
        vwap = curr.get('VWAP', close)
        if vwap > 0:
            dist_to_vwap_pct = abs(close - vwap) / vwap * 100
            if dist_to_vwap_pct > 0.5:
                return False
        
        # 4. Low Movement Check (Last 4 hours)
        # Assuming 1h timeframe, look back 4 candles
        if len(df) >= 5:
            four_h_ago = df.iloc[-5]
            price_change_4h = abs(close - four_h_ago['close']) / four_h_ago['close'] * 100
            if price_change_4h >= 1.0:
                return False
        
        return True
