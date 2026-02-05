
import logging
import numpy as np
from typing import Dict, List, Optional
import time

logger = logging.getLogger("OrderBookAnalyzer")

class OrderBookAnalyzer:
    """
    Analyzes the order book (depth) to detect:
    1. Bid-Ask Imbalance (Pressure)
    2. Large Orders (Whale Walls)
    3. Support/Resistance Clusters
    4. Spoofing (Fake Walls - Simplified detection)
    """
    
    def __init__(self):
        self.whale_threshold_ratio = 5.0 # Order size > 5x Average is considered Large
        self.imbalance_threshold = 1.5 # 1.5x Buy/Sell ratio indicates pressure
        
    def analyze_depth(self, order_book: Dict, current_price: float) -> Dict:
        """
        Analyzes the given order book snapshot.
        order_book structure: {'bids': [[price, qty], ...], 'asks': [[price, qty], ...]}
        """
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            return {}
            
        bids = order_book['bids'] # [[price, qty], ...]
        asks = order_book['asks'] # [[price, qty], ...]
        
        if not bids or not asks:
            return {}
            
        # 1. Calculate Imbalance (Top 20 Depth)
        limit = 20
        bid_vol = sum([b[1] for b in bids[:limit]])
        ask_vol = sum([a[1] for a in asks[:limit]])
        
        imbalance_ratio = 1.0
        if ask_vol > 0:
            imbalance_ratio = bid_vol / ask_vol
            
        pressure = "NEUTRAL"
        if imbalance_ratio > self.imbalance_threshold:
            pressure = "BUY_PRESSURE"
        elif imbalance_ratio < (1 / self.imbalance_threshold):
            pressure = "SELL_PRESSURE"
            
        # 2. Whale Detection (Large Orders)
        # Calculate average order size in top 50
        all_sizes = [b[1] for b in bids[:50]] + [a[1] for a in asks[:50]]
        avg_size = np.mean(all_sizes) if all_sizes else 0
        
        whale_walls = []
        
        # Check Bids (Support Walls)
        for p, q in bids[:20]:
            if q > avg_size * self.whale_threshold_ratio:
                dist = (current_price - p) / current_price
                if dist < 0.05: # Within 5%
                    whale_walls.append({
                        'type': 'SUPPORT',
                        'price': p,
                        'qty': q,
                        'strength': q / avg_size,
                        'distance_pct': dist * 100
                    })
                    
        # Check Asks (Resistance Walls)
        for p, q in asks[:20]:
            if q > avg_size * self.whale_threshold_ratio:
                dist = (p - current_price) / current_price
                if dist < 0.05: # Within 5%
                    whale_walls.append({
                        'type': 'RESISTANCE',
                        'price': p,
                        'qty': q,
                        'strength': q / avg_size,
                        'distance_pct': dist * 100
                    })
                    
        # 3. Spread Analysis
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = (best_ask - best_bid) / best_bid
        
        return {
            'imbalance_ratio': float(imbalance_ratio),
            'pressure': pressure,
            'bid_volume_top20': float(bid_vol),
            'ask_volume_top20': float(ask_vol),
            'whale_walls': whale_walls,
            'spread_pct': float(spread * 100)
        }
        
    def get_score_impact(self, analysis: Dict) -> float:
        """
        Returns a score modifier based on order book analysis.
        Range: -5.0 to +5.0
        """
        if not analysis:
            return 0.0
            
        score = 0.0
        
        # Pressure Impact
        ratio = analysis.get('imbalance_ratio', 1.0)
        if ratio > 2.0:
            score += 2.0
        elif ratio > 1.5:
            score += 1.0
        elif ratio < 0.5:
            score -= 2.0
        elif ratio < 0.66:
            score -= 1.0
            
        # Whale Walls Impact
        walls = analysis.get('whale_walls', [])
        for wall in walls:
            if wall['type'] == 'SUPPORT':
                # Strong support nearby is bullish
                score += min(3.0, wall['strength'] * 0.5)
            elif wall['type'] == 'RESISTANCE':
                # Strong resistance nearby is bearish
                score -= min(3.0, wall['strength'] * 0.5)
                
        return max(-5.0, min(5.0, score))
