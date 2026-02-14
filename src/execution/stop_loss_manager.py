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
        
        # Calculate Duration in Minutes
        duration_minutes = (current_time - entry_time).total_seconds() / 60.0

        # --- 1. DYNAMIC ROI (Freqtrade Style) ---
        if settings.DYNAMIC_ROI_ENABLED:
            # Sort keys to find the correct time bracket
            roi_table = dict(sorted(settings.DYNAMIC_ROI_TABLE.items(), reverse=True))
            target_roi = settings.TAKE_PROFIT_PCT # Default Fallback
            
            for time_threshold, roi_target in roi_table.items():
                if duration_minutes >= time_threshold:
                    target_roi = roi_target
                    break # Found the applicable bracket (since we sorted reverse)
            
            # Check if PnL meets the dynamic target
            if pnl_pct >= target_roi:
                return {
                    'action': 'CLOSE', 
                    'reason': f'DYNAMIC_ROI_HIT (Time: {duration_minutes:.1f}m, Target: {target_roi}%, PnL: {pnl_pct:.2f}%)'
                }

        # 2. Time-Based Exit (Legacy Hard Limits)
        hours_held = duration_minutes / 60.0
        
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
        
        # Determine Stop Distance (ATR Based)
        if atr_value > 0:
            # Tighten stop after partial exit
            multiplier = settings.TRAILING_STOP_TIGHT_MULTIPLIER if position.get('partial_exit_executed') else settings.TRAILING_STOP_ATR_MULTIPLIER
            
            # Sniper Mode Override (Tighter Trailing)
            if position.get('is_sniper_mode', False):
                 multiplier = 2.0
            
            stop_distance = atr_value * multiplier
        else:
            # Fallback to dynamic percentage based on volatility if ATR failed
            # If no DF, assume standard volatility
            # Phase 3 Improvement: Use symbol specific default if possible, or config
            fallback_pct = settings.STOP_LOSS_PCT / 100 # Default %5
            stop_distance = current_price * fallback_pct

        # 3. Trailing Stop Logic
        # FIX: Use 'stop_loss' key to match Executor
        current_stop_price = float(position.get('stop_loss', 0.0))
        entry_price = float(position.get('entry_price', 0.0))
        highest_price = float(position.get('highest_price', entry_price if entry_price > 0 else current_price))
        
        # Update highest price
        if current_price > highest_price:
            highest_price = current_price
        
        # Initial stop setup
        if current_stop_price == 0:
            current_stop_price = entry_price - stop_distance
            # FIX: Return update immediately to save initial stop
            return {'action': 'UPDATE_STOP', 'new_stop_price': current_stop_price, 'new_highest_price': highest_price}

        # --- PRO UPDATE: ATR Based Dynamic Stop ---
        # Stop fiyatını sadece fiyat yükseldiğinde yukarı taşı (Trailing)
        # Ancak, ATR çok arttıysa (volatilite patlaması), stop mesafesini biraz açmak gerekebilir mi?
        # Hayır, genelde trailing stop sıkılaşır.
        
        new_stop_price = current_price - stop_distance
        
        # Step Trailing: Only trail if price advanced at least TRAILING_STEP_PCT above last high
        allow_trail = True
        if settings.TRAILING_STEP_ENABLED and highest_price > 0:
            step_threshold = highest_price * (1 + (settings.TRAILING_STEP_PCT / 100.0))
            if current_price < step_threshold:
                allow_trail = False
        
        # Only move stop UP (Trailing) with step gating
        if allow_trail and new_stop_price > current_stop_price:
            final_stop_price = new_stop_price
            update_stop = True
        else:
            final_stop_price = current_stop_price
            update_stop = False
            
        # Check if Price hit Stop
        if current_price <= final_stop_price:
            return {'action': 'CLOSE', 'reason': f'ATR_TRAILING_STOP_HIT (Price: {current_price:.4f} <= Stop: {final_stop_price:.4f})'}

        # 4. Partial Take Profit
        if not position.get('partial_exit_executed', False):
            if pnl_pct >= settings.PARTIAL_TAKE_PROFIT_PCT:
                return {
                    'action': 'PARTIAL_CLOSE', 
                    'reason': f'PARTIAL_PROFIT_TARGET (PnL: {pnl_pct:.2f}%)',
                    'qty_pct': settings.PARTIAL_EXIT_RATIO,
                    'new_stop_price': final_stop_price,
                    'new_highest_price': highest_price
                }

        # Return update if stop price changed (and no other action taken)
        if update_stop:
             return {'action': 'UPDATE_STOP', 'new_stop_price': final_stop_price, 'new_highest_price': highest_price}

        return {'action': 'NONE', 'new_highest_price': highest_price}
