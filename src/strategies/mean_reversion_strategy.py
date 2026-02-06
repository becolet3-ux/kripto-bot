import pandas as pd
import numpy as np
from typing import Dict, Any

class MeanReversionStrategy:
    """
    Mean Reversion Strategy:
    - RSI < 30 and turning up
    - Price touched Lower Bollinger Band and bouncing
    - MACD Histogram bottomed out
    """
    def __init__(self):
        self.name = "MEAN_REVERSION"
        self.weight = 0.3

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or len(df) < 21:
            return {"action": "HOLD", "score": 0.0, "details": {}}

        curr = df.iloc[-2]
        prev = df.iloc[-3]
        
        # 1. RSI Condition
        rsi = curr['RSI']
        rsi_prev = prev['RSI']
        rsi_oversold = rsi < 35 # Slightly looser than 30 for flexibility
        rsi_rising = rsi > rsi_prev
        
        # 2. Bollinger Band Condition
        # Did price touch/break lower band recently?
        touched_lower = (curr['low'] <= curr['BB_Lower']) or (prev['low'] <= prev['BB_Lower'])
        bouncing = curr['close'] > prev['close']
        
        # 3. MACD Histogram Condition
        # MACD Hist = MACD - Signal
        hist_curr = curr['MACD'] - curr['Signal_Line']
        hist_prev = prev['MACD'] - prev['Signal_Line']
        hist_prev2 = df.iloc[-4]['MACD'] - df.iloc[-4]['Signal_Line']
        
        # Bottoming out: Was negative, now less negative (rising)
        hist_bottoming = (hist_curr < 0) and (hist_curr > hist_prev) and (hist_prev <= hist_prev2)
        
        score = 0.0
        action = "HOLD"
        
        if rsi_oversold:
            score += 3.0
            if rsi_rising:
                score += 1.0
        
        if touched_lower and bouncing:
            score += 2.0
            
        if hist_bottoming:
            score += 1.0
            
        # Threshold for Entry
        if score >= 5.0:
            action = "ENTRY"
            
        return {
            "strategy": self.name,
            "action": action,
            "score": score,
            "details": {
                "rsi": rsi,
                "hist_bottoming": bool(hist_bottoming),
                "touched_lower": bool(touched_lower)
            }
        }
