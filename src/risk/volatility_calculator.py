import pandas as pd
import numpy as np
from typing import Optional

class VolatilityCalculator:
    """
    Calculates volatility based on ATR and Price.
    Used for dynamic position sizing and leverage adjustment.
    """
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculates Average True Range (ATR).
        """
        if df.empty:
            return pd.Series()
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr

    @staticmethod
    def get_volatility_pct(df: pd.DataFrame, period: int = 14) -> float:
        """
        Returns the current volatility as a percentage of price.
        Formula: (ATR / Close) * 100
        """
        if df.empty or len(df) < period:
            return 0.0
            
        atr_series = VolatilityCalculator.calculate_atr(df, period)
        current_atr = atr_series.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        if current_price == 0:
            return 0.0
            
        volatility_pct = (current_atr / current_price) * 100
        return float(volatility_pct)
