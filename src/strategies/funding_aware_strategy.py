from typing import Dict, Optional
from src.collectors.funding_rate_loader import FundingRateLoader
from src.utils.logger import log

class FundingAwareStrategy:
    """
    Phase 4: Funding Rate Integration
    Adjusts trading signals based on Funding Rates.
    """
    def __init__(self, funding_loader: FundingRateLoader):
        self.loader = funding_loader
        
    def analyze_funding(self, symbol: str) -> Dict:
        """
        Analyzes funding rate for a symbol and returns impact details.
        """
        rate = self.loader.get_funding_rate(symbol)
        rate_pct = rate * 100
        
        impact = {
            'funding_rate': rate,
            'funding_rate_pct': rate_pct,
            'action': 'NEUTRAL',
            'score_boost': 0.0,
            'size_boost': 1.0,
            'reason': 'Normal Funding'
        }
        
        # Logic from Phase 4 Requirements
        # Positive Funding (> 0.01%) -> Longs Pay Shorts (Bullish Sentiment usually)
        # Negative Funding (< -0.01%) -> Shorts Pay Longs (Bearish Sentiment usually)
        
        if rate_pct > 0.10:
            # Very High Funding (Strong Bullish Sentiment)
            impact['action'] = 'AGGRESSIVE_LONG'
            impact['score_boost'] = 2.0
            impact['size_boost'] = 1.2 # Increase size by 20%
            impact['reason'] = 'High Positive Funding (>0.10%) - Strong Trend'
            
        elif rate_pct > 0.05:
            # High Funding (Bullish)
            impact['action'] = 'BOOST_LONG'
            impact['score_boost'] = 1.0
            impact['reason'] = 'Positive Funding (>0.05%) - Trend Support'
            
        elif rate_pct < 0.0:
            # Negative Funding (Bearish Sentiment) - ZERO TOLERANCE
            # "Long sinyallerini ignore et"
            impact['action'] = 'IGNORE_LONG'
            impact['score_boost'] = -10.0 # Heavy penalty
            impact['reason'] = 'Negative Funding (<0.0%) - Bearish Pressure'
            
        return impact
