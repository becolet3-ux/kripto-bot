import pandas as pd
import numpy as np
from typing import Dict, Any

class BreakoutStrategy:
    """
    Breakout Strategy:
    - Bollinger Bands Squeeze (Consolidation) followed by Expansion
    - Volume Spike (> 2x Average)
    - Price breaks Upper Bollinger Band
    """
    def __init__(self):
        self.name = "BREAKOUT"
        self.weight = 0.4  # Default weight

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or len(df) < 21:
            return {"action": "HOLD", "score": 0.0, "details": {}}

        curr = df.iloc[-2] # Last completed candle
        prev = df.iloc[-3]
        
        # 1. Bollinger Band Width
        bb_width_curr = (curr['BB_Upper'] - curr['BB_Lower']) / curr['BB_Middle'] if curr['BB_Middle'] > 0 else 0
        bb_width_prev = (prev['BB_Upper'] - prev['BB_Lower']) / prev['BB_Middle'] if prev['BB_Middle'] > 0 else 0
        
        # Squeeze condition (e.g., width was low recently) - Simplified here as "Expansion" check
        # Ideally we want to see if it WAS narrow. Let's check 5 bars ago.
        lookback = 5
        recent_widths = []
        for i in range(3, 3 + lookback):
            if len(df) > i:
                row = df.iloc[-i]
                w = (row['BB_Upper'] - row['BB_Lower']) / row['BB_Middle'] if row['BB_Middle'] > 0 else 0
                recent_widths.append(w)
        
        was_squeezed = any(w < 0.10 for w in recent_widths) if recent_widths else False
        is_expanding = bb_width_curr > bb_width_prev
        
        # 2. Volume Spike
        vol_ratio = curr.get('Volume_Ratio', 0.0)
        has_volume = vol_ratio > 2.0
        
        # 3. Upper Band Breakout
        breakout = curr['close'] > curr['BB_Upper']
        
        score = 0.0
        action = "HOLD"
        
        if breakout:
            score += 3.0
            if has_volume:
                score += 2.0
            if was_squeezed and is_expanding:
                score += 2.0
                
            if score >= 5.0:
                action = "ENTRY"
                
        return {
            "strategy": self.name,
            "action": action,
            "score": score,
            "details": {
                "bb_width": bb_width_curr,
                "vol_ratio": vol_ratio,
                "was_squeezed": was_squeezed,
                "breakout": bool(breakout)
            }
        }
