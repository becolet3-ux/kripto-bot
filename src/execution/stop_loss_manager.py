import talib
import pandas as pd
import numpy as np
from datetime import datetime
from config.settings import settings
from src.utils.logger import log

class StopLossManager:
    def __init__(self):
        pass

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculates ATR value from DataFrame."""
        if df is None or len(df) < period + 1:
            return 0.0
        
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # TA-Lib ATR
            atr = talib.ATR(high, low, close, timeperiod=period)
            
            # Return last valid value
            if np.isnan(atr[-1]):
                return 0.0
            return float(atr[-1])
        except Exception as e:
            log(f"⚠️ ATR Calculation Error: {e}")
            return 0.0

    def check_exit_conditions(self, position: dict, current_price: float, current_time: datetime, df: pd.DataFrame = None) -> dict:
        """
        Checks for Trailing Stop, Partial Take Profit, and Time-Based Exit.
        Returns a dict with 'action' and 'reason'.
        Action can be 'CLOSE', 'PARTIAL_CLOSE', 'UPDATE_STOP', or 'NONE'.
        """
        symbol = position.get('symbol')
        entry_price = float(position.get('entry_price', 0))
        entry_time_str = position.get('entry_timestamp') 
        timestamp_float = position.get('timestamp')
        quantity = float(position.get('quantity', 0))
        
        if entry_price == 0:
            return {'action': 'NONE'}

        # Parse entry time
        if entry_time_str:
            if isinstance(entry_time_str, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time_str)
                except ValueError:
                    entry_time = current_time
            elif isinstance(entry_time_str, datetime):
                entry_time = entry_time_str
            else:
                entry_time = current_time
        elif timestamp_float:
            try:
                entry_time = datetime.fromtimestamp(float(timestamp_float))
            except:
                entry_time = current_time
        else:
            entry_time = current_time # Fallback if missing

        # Calculate PnL %
        pnl_pct = (current_price - entry_price) / entry_price * 100

        # 1. Time-Based Exit
        hours_held = (current_time - entry_time).total_seconds() / 3600
        
        # Hard Stop (48h)
        if hours_held >= settings.MAX_HOLD_TIME_HOURS:
            return {'action': 'CLOSE', 'reason': f'MAX_HOLD_TIME ({hours_held:.1f}h)'}
        
        # Soft Stop (24h with no profit)
        if hours_held >= settings.TIME_BASED_EXIT_HOURS and pnl_pct <= 0:
             return {'action': 'CLOSE', 'reason': f'TIME_BASED_NO_PROFIT ({hours_held:.1f}h)'}

        # 2. Calculate ATR for Trailing Stop
        atr_value = 0.0
        if df is not None:
            atr_value = self.calculate_atr(df)
        
        # Determine Stop Distance
        if atr_value > 0:
            # Tighten stop after partial exit
            multiplier = settings.TRAILING_STOP_TIGHT_MULTIPLIER if position.get('partial_exit_executed') else settings.TRAILING_STOP_ATR_MULTIPLIER
            stop_distance = atr_value * multiplier
        else:
            # Fallback to fixed percentage if ATR failed
            fallback_pct = settings.STOP_LOSS_PCT / 100
            stop_distance = current_price * fallback_pct

        # 3. Trailing Stop Logic
        current_stop_price = float(position.get('trailing_stop_price', 0.0))
        
        # Initial stop setup
        if current_stop_price == 0:
            current_stop_price = entry_price - stop_distance

        new_stop_price = current_price - stop_distance
        
        # Only move stop UP (Trailing)
        if new_stop_price > current_stop_price:
            final_stop_price = new_stop_price
            update_stop = True
        else:
            final_stop_price = current_stop_price
            update_stop = False
            
        # Check if Price hit Stop
        if current_price <= final_stop_price:
            return {'action': 'CLOSE', 'reason': f'TRAILING_STOP_HIT (Price: {current_price:.4f} <= Stop: {final_stop_price:.4f})'}

        # 4. Partial Take Profit
        if not position.get('partial_exit_executed', False):
            if pnl_pct >= settings.PARTIAL_TAKE_PROFIT_PCT:
                return {
                    'action': 'PARTIAL_CLOSE', 
                    'reason': f'PARTIAL_PROFIT_TARGET (PnL: {pnl_pct:.2f}%)',
                    'qty_pct': settings.PARTIAL_EXIT_RATIO,
                    'new_stop_price': final_stop_price
                }

        # Return update if stop price changed (and no other action taken)
        if update_stop:
             return {'action': 'UPDATE_STOP', 'new_stop_price': final_stop_price}

        return {'action': 'NONE'}
