import ccxt
import pandas as pd
import talib as ta
from typing import Dict, Optional, Any
from src.utils.logger import logger
from src.collectors.binance_tr_client import BinanceTRClient

def fetch_data(symbol: str, timeframe: str, exchange: Any, limit: int = 100) -> Optional[pd.DataFrame]:
    """
    Fetches OHLCV data compatible with both CCXT and BinanceTRClient.
    """
    try:
        if isinstance(exchange, BinanceTRClient):
            # BinanceTRClient returns dict with 'data' list of lists
            # Format: [ [time, open, high, low, close, vol, ...], ... ]
            resp = exchange.get_klines(symbol, interval=timeframe, limit=limit)
            if resp.get('code') == 0 and 'data' in resp:
                ohlcv = resp['data']
            else:
                logger.log(f"❌ Error fetching data from BinanceTR for {symbol}: {resp}")
                return None
        else:
            # CCXT Exchange
            if hasattr(exchange, 'fetch_ohlcv'):
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            else:
                logger.log(f"❌ Unknown exchange type: {type(exchange)}")
                return None
                
        if not ohlcv or len(ohlcv) < 50: # Need enough data for indicators
            return None
            
        # Standardize columns
        # CCXT: [timestamp, open, high, low, close, volume]
        # BinanceTR (Global API): [time, open, high, low, close, volume, close_time, quote_vol, trades, ...]
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'] + (['extra']* (len(ohlcv[0])-6) if len(ohlcv[0]) > 6 else []))
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    except Exception as e:
        logger.log(f"❌ Exception fetching data for {symbol} {timeframe}: {e}")
        return None

def analyze_single_timeframe(symbol: str, timeframe: str, exchange: Any) -> Dict:
    """
    Analyzes a single timeframe using technical indicators.
    
    Args:
        symbol (str): Trading pair (e.g., 'BTC/USDT')
        timeframe (str): Timeframe (e.g., '15m', '1h', '4h')
        exchange (Any): CCXT exchange instance or BinanceTRClient
    
    Returns:
        dict: Analysis results
    """
    
    # 1. Fetch Data
    df = fetch_data(symbol, timeframe, exchange)
    if df is None:
        return {
            'direction': 'NEUTRAL',
            'trend_strength': 'WEAK',
            'indicators': {},
            'confidence': 0.0,
            'error': 'Insufficient Data'
        }
    
    # 2. Indicators
    try:
        # --- Trend (EMA Cross) ---
        df['ema_20'] = ta.EMA(df['close'], timeperiod=20)
        df['ema_50'] = ta.EMA(df['close'], timeperiod=50)
        
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        
        ema_cross = 'BULLISH' if ema_20 > ema_50 else 'BEARISH'
        
        # --- Momentum (RSI) ---
        df['rsi'] = ta.RSI(df['close'], timeperiod=14)
        rsi_val = df['rsi'].iloc[-1]
        rsi_signal = 'BULLISH' if rsi_val > 50 else 'BEARISH'
        
        # --- MACD ---
        macd, signal, hist = ta.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        hist_val = hist.iloc[-1]
        macd_signal = 'BULLISH' if hist_val > 0 else 'BEARISH'
        
        # --- ADX (Trend Strength) ---
        df['adx'] = ta.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        adx_val = df['adx'].iloc[-1]
        trend_strength = 'STRONG' if adx_val > 25 else 'WEAK'
        
        # 3. Voting System
        bullish_votes = sum([
            ema_cross == 'BULLISH',
            rsi_signal == 'BULLISH',
            macd_signal == 'BULLISH'
        ])
        
        bearish_votes = 3 - bullish_votes
        
        # 4. Decision
        direction = 'NEUTRAL'
        
        if bullish_votes >= 2 and trend_strength == 'STRONG':
            direction = 'LONG'
        elif bearish_votes >= 2 and trend_strength == 'STRONG':
            direction = 'SHORT'
        elif trend_strength == 'WEAK':
             # Even if votes align, weak trend might mean ranging
             # But let's follow the prompt logic: "else: direction = NEUTRAL"
             # The prompt logic says:
             # if bullish_votes >= 2 and trend_strength == 'STRONG': LONG
             # elif bearish_votes >= 2 and trend_strength == 'STRONG': SHORT
             # else: NEUTRAL
             direction = 'NEUTRAL'
             
        # Optional: Allow Entry in Weak Trend if all 3 indicators agree?
        # Prompt says strict check on STRONG trend. sticking to prompt.
        
        return {
            'direction': direction,
            'trend_strength': trend_strength,
            'indicators': {
                'ema_cross': ema_cross,
                'rsi': rsi_val,
                'macd_hist': hist_val,
                'adx': adx_val
            },
            'confidence': bullish_votes / 3.0 if direction == 'LONG' else (bearish_votes / 3.0 if direction == 'SHORT' else 0.0)
        }
        
    except Exception as e:
        logger.log(f"❌ Analysis error for {symbol} {timeframe}: {e}")
        return {
            'direction': 'NEUTRAL',
            'trend_strength': 'WEAK',
            'indicators': {},
            'confidence': 0.0,
            'error': str(e)
        }

def multi_timeframe_analyzer(symbol: str, exchange: Any) -> Dict:
    """
    Analyzes 3 timeframes (15m, 1h, 4h) and generates a consensus.
    """
    # 1. Analyze Timeframes
    tf_15m = analyze_single_timeframe(symbol, '15m', exchange)
    tf_1h = analyze_single_timeframe(symbol, '1h', exchange)
    tf_4h = analyze_single_timeframe(symbol, '4h', exchange)
    
    # 2. Weights (Conceptually used for importance, but logic is rule-based below)
    # 4h is most important (Trend)
    # 1h is intermediate
    # 15m is entry trigger
    
    # 3. Consensus Logic
    directions = [tf_15m['direction'], tf_1h['direction'], tf_4h['direction']]
    
    # Scenario 1: PERFECT ALIGNMENT (Ideal)
    # All non-neutral and same direction
    if len(set(directions)) == 1 and directions[0] != 'NEUTRAL':
        return {
            'consensus': True,
            'direction': directions[0],
            'confidence_multiplier': 1.30, # %30 bonus
            'timeframes': {
                '15m': tf_15m,
                '1h': tf_1h,
                '4h': tf_4h
            },
            'blocking_reason': None,
            'analysis_summary': f"Perfect alignment - All timeframes {directions[0]}"
        }
        
    # Scenario 2: 15m and 1h align, but 4h is OPPOSITE (DANGEROUS)
    # If 4h is NEUTRAL, it's not "Opposite", just weak.
    # Opposite means LONG vs SHORT.
    if tf_15m['direction'] == tf_1h['direction'] and tf_15m['direction'] != 'NEUTRAL':
        if tf_4h['direction'] != 'NEUTRAL' and tf_4h['direction'] != tf_15m['direction']:
            return {
                'consensus': False,
                'direction': 'NEUTRAL',
                'confidence_multiplier': 0.0,
                'timeframes': {
                    '15m': tf_15m,
                    '1h': tf_1h,
                    '4h': tf_4h
                },
                'blocking_reason': f"4H counter-trend detected. 15m/1h={tf_15m['direction']} but 4h={tf_4h['direction']}",
                'analysis_summary': "Major timeframe divergence - BLOCKED"
            }
            
    # Scenario 3: 4h and 1h align, 15m is different (Acceptable Noise)
    if tf_4h['direction'] == tf_1h['direction'] and tf_4h['direction'] != 'NEUTRAL':
        return {
            'consensus': True,
            'direction': tf_4h['direction'],
            'confidence_multiplier': 1.15, # %15 bonus
            'timeframes': {
                '15m': tf_15m,
                '1h': tf_1h,
                '4h': tf_4h
            },
            'blocking_reason': None,
            'analysis_summary': f"Strong alignment (4h+1h) - 15m noise ignored. Direction: {tf_4h['direction']}"
        }
        
    # Scenario 4: No Consensus / Mixed / Too Neutral
    return {
        'consensus': False,
        'direction': 'NEUTRAL',
        'confidence_multiplier': 0.0,
        'timeframes': {
            '15m': tf_15m,
            '1h': tf_1h,
            '4h': tf_4h
        },
        'blocking_reason': "No clear consensus across timeframes",
        'analysis_summary': f"Mixed signals: 15m={tf_15m['direction']}, 1h={tf_1h['direction']}, 4h={tf_4h['direction']}"
    }
