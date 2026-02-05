import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from pydantic import BaseModel
from config.settings import settings
from src.utils.logger import logger
from src.ml.ensemble_manager import EnsembleManager
from src.market_structure.orderbook_analyzer import OrderBookAnalyzer
from src.market_structure.volume_profile import VolumeProfileAnalyzer

class TradeSignal(BaseModel):
    symbol: str
    action: str  # "ENTRY", "EXIT", "HOLD"
    direction: str # "LONG", "SHORT", "LONG_SPOT_SHORT_PERP"
    score: float
    estimated_yield: float
    timestamp: int
    details: Dict

class MarketAnalyzer:
    def __init__(self):
        # Spot Strategy Parameters
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.sma_short_period = 7
        self.sma_long_period = 25
        
        # ML Ensemble Manager
        self.ensemble = EnsembleManager()
        # Order Book Analyzer
        self.orderbook_analyzer = OrderBookAnalyzer()
        # Volume Profile Analyzer
        self.vp_analyzer = VolumeProfileAnalyzer()

    def calculate_indicators(self, candles: List[List]) -> pd.DataFrame:
        """
        Calculates RSI and Moving Averages using Pandas.
        Candles format: [timestamp, open, high, low, close, volume]
        """
        if not candles or len(candles) < self.sma_long_period:
            return pd.DataFrame()

        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        
        # SMA
        df['SMA_Short'] = df['close'].rolling(window=self.sma_short_period).mean()
        df['SMA_Long'] = df['close'].rolling(window=self.sma_long_period).mean()
        
        # Volume Analysis
        df['SMA_Volume'] = df['volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['volume'] / df['SMA_Volume']
        
        # Volatility (Standard Deviation of Returns)
        df['Returns'] = df['close'].pct_change()
        df['Volatility'] = df['Returns'].rolling(window=20).std() * 100 # In percentage
        
        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['close'].rolling(window=20).mean()
        df['BB_Std'] = df['close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Stochastic RSI
        min_val = df['RSI'].rolling(window=14).min()
        max_val = df['RSI'].rolling(window=14).max()
        denom = max_val - min_val
        df['Stoch_RSI'] = np.where(denom == 0, 0.5, (df['RSI'] - min_val) / denom)
        
        # --- SuperTrend Calculation ---
        atr_period = 10
        atr_multiplier = 3.0
        
        # ATR
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=atr_period).mean()
        
        # Basic Bands
        hl2 = (df['high'] + df['low']) / 2
        df['ST_Upper_Basic'] = hl2 + (atr_multiplier * df['ATR'])
        df['ST_Lower_Basic'] = hl2 - (atr_multiplier * df['ATR'])
        
        # Final Bands
        df['ST_Upper'] = df['ST_Upper_Basic']
        df['ST_Lower'] = df['ST_Lower_Basic']
        df['SuperTrend'] = df['ST_Upper'] # Default init
        df['ST_Direction'] = 1 # 1: Bullish (Price > ST), -1: Bearish
        
        # Iterative calculation for SuperTrend (requires loop as it depends on previous values)
        # Note: Vectorizing this fully is hard, using a fast loop
        st_upper = df['ST_Upper_Basic'].values
        st_lower = df['ST_Lower_Basic'].values
        close = df['close'].values
        st = np.zeros(len(df))
        direction = np.zeros(len(df))
        
        # Init first value
        st[0] = st_upper[0]
        direction[0] = 1
        
        for i in range(1, len(df)):
            # Final Upper Band
            if st_upper[i] < st_upper[i-1] or close[i-1] > st_upper[i-1]:
                st_upper[i] = st_upper[i]
            else:
                st_upper[i] = st_upper[i-1]
                
            # Final Lower Band
            if st_lower[i] > st_lower[i-1] or close[i-1] < st_lower[i-1]:
                st_lower[i] = st_lower[i]
            else:
                st_lower[i] = st_lower[i-1]
                
            # SuperTrend Logic
            if direction[i-1] == 1: # Was Bullish
                if close[i] <= st_lower[i-1]: # Breakdown
                    direction[i] = -1
                    st[i] = st_upper[i]
                else:
                    direction[i] = 1
                    st[i] = st_lower[i]
            else: # Was Bearish
                if close[i] >= st_upper[i-1]: # Breakout
                    direction[i] = 1
                    st[i] = st_lower[i]
                else:
                    direction[i] = -1
                    st[i] = st_upper[i]
                    
        df['SuperTrend'] = st
        df['ST_Direction'] = direction

        # --- CCI (Commodity Channel Index) ---
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=20).mean()
        mad = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        df['CCI'] = (tp - sma_tp) / (0.015 * mad)

        # --- ADX (Average Directional Index) ---
        # TR is already calculated above
        up_move = df['high'].diff()
        down_move = -df['low'].diff()
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        # Smooth DM and TR (Wilder's Smoothing usually 14)
        adx_period = 14
        df['plus_di'] = 100 * pd.Series(plus_dm).ewm(alpha=1/adx_period, adjust=False).mean() / df['TR'].ewm(alpha=1/adx_period, adjust=False).mean()
        df['minus_di'] = 100 * pd.Series(minus_dm).ewm(alpha=1/adx_period, adjust=False).mean() / df['TR'].ewm(alpha=1/adx_period, adjust=False).mean()
        
        dx = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['ADX'] = dx.ewm(alpha=1/adx_period, adjust=False).mean()

        # --- MFI (Money Flow Index) ---
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = np.where(typical_price > typical_price.shift(1), money_flow, 0)
        negative_flow = np.where(typical_price < typical_price.shift(1), money_flow, 0)
        
        positive_mf = pd.Series(positive_flow).rolling(window=14).sum()
        negative_mf = pd.Series(negative_flow).rolling(window=14).sum()
        
        mfi_ratio = positive_mf / negative_mf
        df['MFI'] = 100 - (100 / (1 + mfi_ratio))

        # --- VWAP (Volume Weighted Average Price) ---
        # Rolling VWAP over the loaded window (usually 500 candles)
        # For intraday, typically anchored to start of day, but rolling 24h (approx 24 candles for 1h) is also useful.
        # Here we calculate Cumulative VWAP for the dataframe window to see the "Session" fair price.
        cum_pv = (typical_price * df['volume']).cumsum()
        cum_vol = df['volume'].cumsum()
        df['VWAP'] = cum_pv / cum_vol
        
        # Also useful: Rolling VWAP (e.g., 24 periods for 1h chart ~ 1 day)
        df['VWAP_24'] = (typical_price * df['volume']).rolling(window=24).sum() / df['volume'].rolling(window=24).sum()

        # --- Pattern Recognition (Simple) ---
        # 1. Doji: Open and Close are very close
        body_size = abs(df['close'] - df['open'])
        candle_range = df['high'] - df['low']
        df['is_doji'] = body_size <= (candle_range * 0.1) # Body is less than 10% of range
        
        # 2. Hammer: Small body at top, long lower wick
        lower_wick = np.minimum(df['open'], df['close']) - df['low']
        upper_wick = df['high'] - np.maximum(df['open'], df['close'])
        df['is_hammer'] = (lower_wick > 2 * body_size) & (upper_wick < body_size)
        
        # 3. Bullish Engulfing
        # Previous candle red, Current candle green, Current body covers previous body
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        df['is_bullish_engulfing'] = (
            (df['close'] > df['open']) & # Green
            (prev_close < prev_open) & # Red
            (df['open'] < prev_close) & # Open lower than prev close
            (df['close'] > prev_open)   # Close higher than prev open
        )

        return df

    def analyze_market_regime(self, candles: List[List]) -> Dict[str, str]:
        """
        Analyzes the market regime based on BTC (or Index) candles.
        Returns: {'trend': 'UP'|'DOWN'|'SIDEWAYS', 'volatility': 'HIGH'|'LOW'}
        """
        df = self.calculate_indicators(candles)
        if df.empty:
            return {'trend': 'SIDEWAYS', 'volatility': 'LOW'}
            
        last = df.iloc[-2]
        
        # Trend Detection using SMA50 vs SMA200 (if available) or SMA25
        # Since we use SMA_Long (25) in calculate_indicators, let's use that as proxy for now
        sma_long = last['SMA_Long']
        close = last['close']
        
        # Bollinger Band Width for Volatility
        bb_upper = last['BB_Upper']
        bb_lower = last['BB_Lower']
        bb_middle = last['BB_Middle']
        
        bb_width = 0
        if bb_middle > 0:
            bb_width = (bb_upper - bb_lower) / bb_middle
        
        trend = "SIDEWAYS"
        if close > sma_long * 1.005: # 0.5% buffer
            trend = "UP"
        elif close < sma_long * 0.995:
            trend = "DOWN"
            
        volatility = "LOW"
        if bb_width > 0.05: # 5% width is decent volatility for 1h
            volatility = "HIGH"
            
        return {'trend': trend, 'volatility': volatility}

    def calculate_correlation(self, candles1: List[List], candles2: List[List]) -> float:
        """
        Calculates Pearson correlation coefficient between two sets of candles.
        Returns value between -1.0 and 1.0
        """
        if not candles1 or not candles2:
            return 0.0
            
        # Create DataFrames
        df1 = pd.DataFrame(candles1, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df2 = pd.DataFrame(candles2, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Ensure 'close' is float
        df1['close'] = df1['close'].astype(float)
        df2['close'] = df2['close'].astype(float)
        
        # Merge on timestamp to align data
        merged = pd.merge(df1[['timestamp', 'close']], df2[['timestamp', 'close']], on='timestamp', suffixes=('_1', '_2'))
        
        if len(merged) < 20: # Need enough data points
            return 0.0
            
        return merged['close_1'].corr(merged['close_2'])

    def analyze_spot(self, symbol: str, candles: List[List], 
                     rsi_modifier: float = 0, is_blocked: bool = False, 
                     weights: Dict[str, float] = None, 
                     indicator_weights: Dict[str, float] = None, 
                     market_regime: Dict = None, 
                     sentiment_score: float = 0.0,
                     order_book: Optional[Dict] = None) -> Optional[TradeSignal]:
        """
        Spot Strategy: Trend Following + RSI + Volume/Volatility Checks + Sentiment + Indicator Consensus
        """
        if weights is None:
            weights = {}
        if indicator_weights is None:
            indicator_weights = {
                "rsi": 1.0, "macd": 1.0, "super_trend": 1.0, 
                "sma_trend": 1.0, "bollinger": 1.0, "stoch_rsi": 1.0,
                "cci": 1.0, "adx": 1.0, "mfi": 1.0, "patterns": 1.0,
                "vwap": 1.0 # VWAP Weight
            }

        # Default weights if not provided
        w_trend = weights.get("trend_following", 1.0)
        w_cross = weights.get("golden_cross", 1.0)
        w_oversold = weights.get("oversold_bounce", 1.0)
        w_sentiment = weights.get("sentiment", 0.5) # Weight for sentiment impact
        
        # Adjust weights based on Market Regime
        if market_regime:
            if market_regime['trend'] == 'UP':
                w_trend *= 1.2
                w_cross *= 1.2
                w_oversold *= 0.8 # Don't bet against the trend too much
            elif market_regime['trend'] == 'SIDEWAYS':
                w_trend *= 0.8
                w_oversold *= 1.5 # Range trading is better here
        
        df = self.calculate_indicators(candles)
        if df.empty:
            return None
            
        # Use the last COMPLETED candle for analysis (index -2) to avoid repainting
        # Index -1 is the current (open) candle.
        last_row = df.iloc[-2]
        prev_row = df.iloc[-3]
        
        # Extract Values
        rsi = last_row['RSI']
        sma_short = last_row['SMA_Short']
        sma_long = last_row['SMA_Long']
        vol_ratio = last_row.get('Volume_Ratio', 1.0)
        volatility = last_row.get('Volatility', 0.0)
        macd = last_row.get('MACD', 0.0)
        macd_signal = last_row.get('Signal_Line', 0.0)
        bb_upper = last_row.get('BB_Upper', 0.0)
        bb_lower = last_row.get('BB_Lower', 0.0)
        stoch_rsi = last_row.get('Stoch_RSI', 0.5)
        super_trend = last_row.get('SuperTrend', 0.0)
        st_direction = last_row.get('ST_Direction', 1)
        cci = last_row.get('CCI', 0.0)
        adx = last_row.get('ADX', 0.0)
        plus_di = last_row.get('plus_di', 0.0)
        minus_di = last_row.get('minus_di', 0.0)
        mfi = last_row.get('MFI', 50.0)
        vwap = last_row.get('VWAP', 0.0) # Cumulative VWAP
        is_doji = last_row.get('is_doji', False)
        is_hammer = last_row.get('is_hammer', False)
        is_bullish_engulfing = last_row.get('is_bullish_engulfing', False)
        close = float(last_row['close'])
        
        # Volume Profile Check (Support/Resistance)
        # vp = self.calculate_volume_profile(candles)
        # poc = vp.get('poc', 0)
        
        # Check for Golden Cross (Short crosses above Long)
        golden_cross = prev_row['SMA_Short'] <= prev_row['SMA_Long'] and sma_short > sma_long
        
        # Check for Death Cross (Short crosses below Long)
        death_cross = prev_row['SMA_Short'] >= prev_row['SMA_Long'] and sma_short < sma_long
        
        action = "HOLD"
        score = 0.0
        primary_strategy = "unknown"
        
        # --- Dynamic Indicator Scoring ---
        # Calculate raw signals (1: Bullish, -1: Bearish, 0: Neutral)
        ind_signals = {}
        
        # 1. RSI (Mean Reversion)
        if rsi < 30: ind_signals['rsi'] = 1
        elif rsi > 70: ind_signals['rsi'] = -1
        else: ind_signals['rsi'] = 0
            
        # 2. MACD (Trend)
        if macd > macd_signal: ind_signals['macd'] = 1
        else: ind_signals['macd'] = -1
            
        # 3. SuperTrend (Trend)
        ind_signals['super_trend'] = int(st_direction)
        
        # 4. SMA Trend (Trend)
        if sma_short > sma_long: ind_signals['sma_trend'] = 1
        else: ind_signals['sma_trend'] = -1
            
        # 5. Bollinger Bands (Mean Reversion)
        if close < bb_lower: ind_signals['bollinger'] = 1
        elif close > bb_upper: ind_signals['bollinger'] = -1
        else: ind_signals['bollinger'] = 0
            
        # 6. Stoch RSI (Momentum)
        if stoch_rsi < 0.2: ind_signals['stoch_rsi'] = 1
        elif stoch_rsi > 0.8: ind_signals['stoch_rsi'] = -1
        else: ind_signals['stoch_rsi'] = 0

        # 7. CCI (Momentum)
        if cci < -100: ind_signals['cci'] = 1
        elif cci > 100: ind_signals['cci'] = -1
        else: ind_signals['cci'] = 0

        # 8. ADX (Trend Strength)
        if adx > 25: # Strong Trend
            if plus_di > minus_di: ind_signals['adx'] = 1
            else: ind_signals['adx'] = -1
        else:
            ind_signals['adx'] = 0
            
        # 9. MFI (Volume-weighted RSI)
        if mfi < 20: ind_signals['mfi'] = 1
        elif mfi > 80: ind_signals['mfi'] = -1
        else: ind_signals['mfi'] = 0
        
        # 10. Patterns (Price Action)
        # Patterns are rare but high probability. We only assign 1 (Bullish) or 0 (Neutral/Bearish logic simplified)
        if is_bullish_engulfing or is_hammer:
            ind_signals['patterns'] = 1
        else:
            ind_signals['patterns'] = 0
            
        # 11. VWAP (Fair Value Analysis)
        # If Price < VWAP -> Undervalued (Bullish/Cheap)
        # If Price > VWAP -> Overvalued (Bearish/Expensive)
        if vwap > 0:
            if close < vwap:
                # But careful, if it's TOO far below, it might be crashing.
                # Ideally we want it slightly below or crossing up.
                # For simplicity: Cheap is good.
                ind_signals['vwap'] = 1
            else:
                ind_signals['vwap'] = -1
        else:
            ind_signals['vwap'] = 0
        
        # Calculate Weighted Indicator Score
        # We sum (Signal * Weight). Since weights can be large (up to 5.0), we normalize or scale.
        # Let's say each indicator contributes +/- 1.0 * Weight to the final score.
        indicator_score = 0.0
        for ind, signal in ind_signals.items():
            weight = indicator_weights.get(ind, 1.0)
            indicator_score += signal * weight
            
        # Add Indicator Score to Base Score (Scaled down slightly to not overpower logic)
        # Assuming average weight is 1.0, 6 indicators -> +/- 6 points max.
        score += indicator_score * 0.5 

        # --- ML Ensemble Score ---
        # Get probability from Ensemble Models (RandomForest, XGBoost, LightGBM)
        # Default is 0.5 (Neutral) if models are not trained.
        ml_prob = self.ensemble.predict_proba(df)
        
        # Map Probability to Score:
        # 0.5 -> 0.0
        # 0.8 -> +6.0
        # 0.2 -> -6.0
        ml_score_contribution = (ml_prob - 0.5) * 20.0
        score += ml_score_contribution
        
        # --- Order Book Analysis Score ---
        ob_analysis = {}
        if order_book:
            ob_analysis = self.orderbook_analyzer.analyze_depth(order_book, close)
            ob_score = self.orderbook_analyzer.get_score_impact(ob_analysis)
            score += ob_score
            
            # Log whale walls if significant
            if ob_score != 0:
                logger.log(f"{symbol} OrderBook Score Impact: {ob_score:.2f} | Imbalance: {ob_analysis.get('imbalance_ratio', 1.0):.2f}")

        # --- Volume Profile Analysis Score ---
        vp_profile = self.vp_analyzer.calculate_profile(candles)
        vp_score, vp_reason = self.vp_analyzer.get_score_impact(close, vp_profile)
        score += vp_score
        if vp_score != 0:
             logger.log(f"{symbol} VP Score: {vp_score} | Reason: {vp_reason}")

        # Dynamic RSI Threshold
        current_rsi_limit = self.rsi_overbought + rsi_modifier
        
        # ENTRY LOGIC (Only if not blocked)
        if not is_blocked:
            # 1. Trend Following (Golden Cross)
            if sma_short > sma_long:
                score += 5.0 * w_trend
                primary_strategy = "trend_following"
                
                # VWAP Logic for Trend
                if vwap > 0:
                    if close < vwap:
                        score += 1.0 # Buy the dip in uptrend
                    elif close > vwap * 1.05:
                        score -= 1.0 # Extended
                
                if rsi < current_rsi_limit:
                    score += 3.0 # Strong Trend, not overbought
                    if golden_cross:
                        action = "ENTRY"
                        score += 10.0 * w_cross # Boost
                        primary_strategy = "golden_cross"
                        
                        # Boost score if Volume is supporting (Volume > Average)
                        if vol_ratio > 1.2:
                            score += 2.0
                else:
                    score -= 2.0 # Overbought, caution
            
            # SuperTrend Confirmation (New)
            if st_direction == 1:
                score += 2.0
            else:
                score -= 2.0

            # 2. Oversold Bounce (RSI < 30) - Catch the bottom
            if rsi < 30:
                action = "ENTRY"
                # If it was already entry from Golden Cross, we keep the higher score or combine?
                score = max(score, 9.0 * w_oversold + (indicator_score * 0.5)) 
                if score >= 9.0 * w_oversold:
                    primary_strategy = "oversold_bounce"
            
            # 3. Sentiment Impact
            if sentiment_score != 0:
                # Normalize sentiment impact (assuming score is -1 to 1)
                sentiment_impact = sentiment_score * 5.0 * w_sentiment
                score += sentiment_impact
                
                # If sentiment is very negative, it can veto a weak buy signal
                if sentiment_score < -0.5 and score < 8.0:
                    action = "HOLD"
                    primary_strategy = "blocked_by_sentiment"
        
        # EXIT LOGIC (Always allowed)
        elif sma_short < sma_long:
            score -= 5.0
            if death_cross:
                action = "EXIT" # Or SELL
                score -= 10.0
            if st_direction == -1: # SuperTrend Bearish
                score -= 5.0

        # Data Collection for ML
        # Save snapshot if significant score or random sample (1%)
        if abs(score) > 5.0 or np.random.random() < 0.01:
            self.ensemble.save_snapshot(df, symbol)

        return TradeSignal(
            symbol=symbol,
            action=action,
            direction="LONG",
            score=score,
            estimated_yield=0.0,
            timestamp=int(last_row['timestamp']),
            details={
                "rsi": float(rsi),
                "macd": float(macd),
                "super_trend": float(super_trend),
                "st_direction": int(st_direction),
                "vwap": float(vwap),
                "atr": float(last_row.get('ATR', 0.0)),
                "ATR": float(last_row.get('ATR', 0.0)), # Capitalized for consistency
                "close": float(close),
                "ml_prob": float(ml_prob),
                "indicators": ind_signals,
                "price_history": df['close'].astype(float).tail(50).tolist() # Last 50 candles for correlation
            }
        )

    def analyze(self, market_data: Dict) -> Optional[TradeSignal]:
        # Legacy Arbitrage Analyzer (Disabled for now)
        return None
