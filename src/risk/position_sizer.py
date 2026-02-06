from typing import Tuple, Dict
import pandas as pd
from config.settings import settings
from src.risk.volatility_calculator import VolatilityCalculator
from src.utils.logger import log

class PositionSizer:
    """
    Manages dynamic position sizing and leverage based on market volatility.
    Phase 2 Improvement: Volatility-Based Position Sizing
    """
    
    def __init__(self):
        self.vol_calculator = VolatilityCalculator()
        
    def calculate_position_params(self, symbol: str, df: pd.DataFrame, total_balance: float, regime: str = 'NEUTRAL') -> Dict:
        """
        Calculates optimal position size and leverage based on volatility using DataFrame.
        """
        # 1. Calculate Volatility
        vol_pct = self.vol_calculator.get_volatility_pct(df)
        
        # Get current price for context if needed, though get_volatility_params handles logic
        return self._get_params(vol_pct, total_balance, symbol, regime)

    def calculate_params_from_atr(self, symbol: str, atr_value: float, price: float, total_balance: float, regime: str = 'NEUTRAL') -> Dict:
        """
        Calculates optimal position size and leverage using pre-calculated ATR and Price.
        """
        if price <= 0:
            return {'position_cost_usdt': 0.0, 'leverage': 1, 'volatility_pct': 0.0, 'risk_level': 'UNKNOWN'}
            
        vol_pct = (atr_value / price) * 100
        return self._get_params(vol_pct, total_balance, symbol, regime)

    def _get_params(self, vol_pct: float, total_balance: float, symbol: str, regime: str = 'NEUTRAL') -> Dict:
        """
        Internal logic to determine params based on volatility percentage.
        """
        # 2. Determine Risk Category and Parameters
        if vol_pct < settings.VOLATILITY_LOW_THRESHOLD:
            risk_level = 'LOW'
            target_leverage = settings.LEVERAGE_LOW_VOL
            pos_size_pct = settings.POS_SIZE_LOW_VOL_PCT
        elif vol_pct > settings.VOLATILITY_HIGH_THRESHOLD:
            risk_level = 'HIGH'
            target_leverage = settings.LEVERAGE_HIGH_VOL
            pos_size_pct = settings.POS_SIZE_HIGH_VOL_PCT
        else:
            risk_level = 'MEDIUM'
            target_leverage = settings.LEVERAGE_MED_VOL
            pos_size_pct = settings.POS_SIZE_MED_VOL_PCT
            
        # Phase 3: Regime Adjustment
        # Adjust size based on regime, but respect High Volatility safety
        if regime == 'TRENDING':
            # Aggressive in Trend
            if risk_level != 'HIGH':
                pos_size_pct = max(pos_size_pct, 35.0)
        elif regime == 'RANGING':
            # Conservative in Range
            pos_size_pct = min(pos_size_pct, 15.0)
            
        # 3. Calculate Position Size Amount
        position_cost = total_balance * (pos_size_pct / 100.0)
        
        # Log the decision
        log(f"📉 Volatility Analysis for {symbol}: {vol_pct:.2f}% ({risk_level}) | Regime: {regime}")
        log(f"🎯 Recommended: Leverage {target_leverage}x, Size {pos_size_pct}% (${position_cost:.2f})")
        
        return {
            'position_cost_usdt': position_cost,
            'leverage': target_leverage,
            'volatility_pct': vol_pct,
            'risk_level': risk_level
        }
