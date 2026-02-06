import pandas as pd
import numpy as np
from typing import Dict, Any

class MomentumStrategy:
    """
    Momentum Strategy:
    - Strong Trend (ADX > 30)
    - SuperTrend Bullish
    - MACD Golden Cross
    """
    def __init__(self):
        self.name = "MOMENTUM"
        self.weight = 0.3

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or len(df) < 21:
            return {"action": "HOLD", "score": 0.0, "details": {}}

        curr = df.iloc[-2]
        prev = df.iloc[-3]
        
        # 1. ADX Strength
        adx = curr.get('ADX', 0)
        strong_trend = adx > 25 # 30 might be too strict, 25 is standard
        very_strong_trend = adx > 35
        
        # 2. SuperTrend
        st_bullish = curr.get('ST_Direction', 0) == 1
        
        # 3. MACD Golden Cross
        # Cross happened recently or is maintained positive gap?
        # Strict Cross: Prev MACD < Signal AND Curr MACD > Signal
        macd_cross = (prev['MACD'] <= prev['Signal_Line']) and (curr['MACD'] > curr['Signal_Line'])
        macd_bullish = curr['MACD'] > curr['Signal_Line']
        
        score = 0.0
        action = "HOLD"
        
        if strong_trend:
            score += 2.0
            if very_strong_trend:
                score += 1.0
                
        if st_bullish:
            score += 3.0
            
        if macd_cross:
            score += 2.0
        elif macd_bullish:
            score += 1.0 # Ongoing bullish momentum
            
        # Threshold
        if score >= 6.0:
            action = "ENTRY"
            
        return {
            "strategy": self.name,
            "action": action,
            "score": score,
            "details": {
                "adx": adx,
                "st_bullish": bool(st_bullish),
                "macd_cross": bool(macd_cross)
            }
        }
