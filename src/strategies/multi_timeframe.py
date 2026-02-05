from typing import Dict, List
import pandas as pd
import numpy as np

class MultiTimeframeAnalyzer:
    """Çoklu zaman dilimi analizi"""
    
    TIMEFRAMES = {
        '15m': {'weight': 0.2, 'description': 'Short-term momentum'},
        '1h': {'weight': 0.4, 'description': 'Primary trend'},
        '4h': {'weight': 0.3, 'description': 'Medium-term confirmation'},
        '1d': {'weight': 0.1, 'description': 'Long-term bias'}
    }
    
    def analyze(self, symbol: str, loader) -> Dict:
        """Tüm timeframe'lerde analiz yap"""
        
        signals = {}
        weighted_score = 0
        
        for tf, config in self.TIMEFRAMES.items():
            # Veri çek
            # loader expects symbol and interval
            try:
                data = loader.fetch_ohlcv(symbol, interval=tf, limit=100)
            except Exception as e:
                print(f"Error fetching data for {symbol} {tf}: {e}")
                continue
            
            if data is None or len(data) < 50:
                continue
                
            # Convert list of lists to DataFrame if necessary
            # Assuming loader returns list of lists [timestamp, open, high, low, close, volume]
            # or it might return a DataFrame. Let's assume list of lists based on other files.
            if isinstance(data, list):
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['close'] = df['close'].astype(float)
            else:
                df = data
            
            # Teknik analiz
            signal = self.analyze_timeframe(df, tf)
            signals[tf] = signal
            
            # Ağırlıklı skor
            weighted_score += signal['score'] * config['weight']
        
        return {
            'symbol': symbol,
            'overall_score': weighted_score,
            'timeframe_signals': signals,
            'alignment': self.check_alignment(signals),
            'recommendation': self.get_recommendation(weighted_score, signals)
        }
    
    def analyze_timeframe(self, data: pd.DataFrame, timeframe: str) -> Dict:
        """Tek bir timeframe analizi"""
        
        # İndikatörler
        sma7 = data['close'].rolling(7).mean().iloc[-1]
        sma25 = data['close'].rolling(25).mean().iloc[-1]
        rsi = self.calculate_rsi(data['close'], 14).iloc[-1]
        macd = self.calculate_macd(data['close'])
        
        score = 0
        reasons = []
        
        # Trend analizi
        if sma7 > sma25:
            score += 3
            reasons.append(f"Uptrend ({timeframe})")
        else:
            score -= 2
            reasons.append(f"Downtrend ({timeframe})")
        
        # Momentum
        if 30 < rsi < 70:
            score += 2
            reasons.append(f"Healthy momentum ({timeframe})")
        elif rsi < 30:
            score += 1
            reasons.append(f"Oversold ({timeframe})")
        elif rsi > 70:
            score -= 2
            reasons.append(f"Overbought ({timeframe})")
        
        # MACD
        if macd['histogram'].iloc[-1] > 0:
            score += 1
        
        return {
            'timeframe': timeframe,
            'score': max(0, min(10, score)),  # 0-10 arası normalize et
            'trend': 'UP' if sma7 > sma25 else 'DOWN',
            'rsi': float(rsi),
            'reasons': reasons
        }
    
    def check_alignment(self, signals: Dict) -> Dict:
        """Timeframe uyumunu kontrol et"""
        
        trends = [s['trend'] for s in signals.values()]
        up_count = trends.count('UP')
        total = len(trends)
        
        alignment_pct = (up_count / total) * 100 if total > 0 else 0
        
        return {
            'aligned': alignment_pct >= 75 or alignment_pct <= 25,
            'alignment_pct': alignment_pct,
            'direction': 'UP' if alignment_pct >= 75 else 'DOWN' if alignment_pct <= 25 else 'MIXED'
        }
    
    def get_recommendation(self, overall_score: float, signals: Dict) -> str:
        """Öneri ver"""
        
        alignment = self.check_alignment(signals)
        
        if overall_score >= 7 and alignment['aligned'] and alignment['direction'] == 'UP':
            return "STRONG_BUY"
        elif overall_score >= 5 and alignment['direction'] == 'UP':
            return "BUY"
        elif overall_score <= 3 and alignment['aligned'] and alignment['direction'] == 'DOWN':
            return "STRONG_SELL"
        elif overall_score <= 4:
            return "SELL"
        else:
            return "HOLD"

    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesapla"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, series: pd.Series) -> pd.DataFrame:
        """MACD hesapla"""
        exp12 = series.ewm(span=12, adjust=False).mean()
        exp26 = series.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return pd.DataFrame({'macd': macd, 'signal': signal, 'histogram': histogram})
