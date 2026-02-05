import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class VolumeProfileAnalyzer:
    """
    Analyzes Volume Profile (Price vs Volume) to find:
    - POC (Point of Control): The price level with the highest traded volume.
    - VAH (Value Area High): The highest price within the Value Area (70% of volume).
    - VAL (Value Area Low): The lowest price within the Value Area.
    - VWAP (Volume Weighted Average Price): Average price weighted by volume.
    """
    def __init__(self, n_bins: int = 100, value_area_pct: float = 0.70):
        self.n_bins = n_bins
        self.value_area_pct = value_area_pct

    def calculate_profile(self, candles: List[List]) -> Dict:
        """
        Calculates Volume Profile metrics from a list of candles.
        Candles format: [timestamp, open, high, low, close, volume]
        """
        if not candles or len(candles) < 10:
            return {}

        try:
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)

            # Determine Range
            min_price = df['low'].min()
            max_price = df['high'].max()
            
            if min_price == max_price:
                return {}

            # Create Price Bins
            price_step = (max_price - min_price) / self.n_bins
            bins = np.linspace(min_price, max_price, self.n_bins + 1)
            
            # We assume volume is distributed uniformly across the candle's range for simplicity
            # A more advanced way is to treat 'close' or 'typical price' as the volume location
            # Here we use 'close' for speed, or Typical Price ((H+L+C)/3)
            df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
            
            # Aggregate volume by price bins
            # cut categorizes 'typical_price' into bins
            df['bin'] = pd.cut(df['typical_price'], bins=bins, include_lowest=True, labels=False)
            
            # Group by bin and sum volume
            volume_profile = df.groupby('bin')['volume'].sum()
            
            # Find POC (Point of Control) - Bin with max volume
            max_vol_bin = volume_profile.idxmax()
            # POC Price is the midpoint of the bin
            poc_price = bins[max_vol_bin] + (price_step / 2)
            
            # Calculate Value Area (VA)
            total_volume = volume_profile.sum()
            target_volume = total_volume * self.value_area_pct
            
            # Start from POC and expand out
            current_vol = volume_profile.get(max_vol_bin, 0)
            
            # Pointers
            upper_idx = int(max_vol_bin)
            lower_idx = int(max_vol_bin)
            
            # Expand until we reach 70%
            while current_vol < target_volume:
                # Look at next upper and lower bins
                upper_vol = volume_profile.get(upper_idx + 1, 0) if (upper_idx + 1) < self.n_bins else 0
                lower_vol = volume_profile.get(lower_idx - 1, 0) if (lower_idx - 1) >= 0 else 0
                
                if upper_vol == 0 and lower_vol == 0:
                    break
                    
                if upper_vol > lower_vol:
                    upper_idx += 1
                    current_vol += upper_vol
                else:
                    lower_idx -= 1
                    current_vol += lower_vol
            
            # Determine VAH and VAL
            vah = bins[upper_idx + 1] # Upper bound of the highest bin
            val = bins[lower_idx]     # Lower bound of the lowest bin
            
            return {
                'poc': float(poc_price),
                'vah': float(vah),
                'val': float(val),
                'total_volume': float(total_volume),
                'range_high': float(max_price),
                'range_low': float(min_price)
            }
            
        except Exception as e:
            logger.error(f"Volume Profile Error: {e}")
            return {}

    def get_score_impact(self, current_price: float, profile: Dict) -> Tuple[float, str]:
        """
        Analyzes the current price relative to the Volume Profile.
        Returns a score impact (-5.0 to +5.0) and a reason string.
        """
        if not profile:
            return 0.0, "No Profile"

        poc = profile['poc']
        vah = profile['vah']
        val = profile['val']
        
        score = 0.0
        reason = "Neutral"
        
        # Logic 1: Rejection from VAL (Support) -> Bullish
        # If price is near VAL (within 1%) and bouncing up
        if val * 0.99 <= current_price <= val * 1.01:
            score = 2.0
            reason = "Near VAL (Support Zone)"
        
        # Logic 2: Rejection from VAH (Resistance) -> Bearish
        # If price is near VAH (within 1%)
        elif vah * 0.99 <= current_price <= vah * 1.01:
            score = -2.0
            reason = "Near VAH (Resistance Zone)"
            
        # Logic 3: Trading Above VAH -> Bullish Breakout
        elif current_price > vah:
            score = 3.0
            reason = "Above VAH (Breakout Zone)"
            
        # Logic 4: Trading Below VAL -> Bearish Breakdown
        elif current_price < val:
            score = -3.0
            reason = "Below VAL (Weak Zone)"
            
        # Logic 5: Near POC -> Neutral / Chop
        elif poc * 0.99 <= current_price <= poc * 1.01:
            score = 0.0
            reason = "At POC (High Liquidity/Chop)"
            
        # Logic 6: Inside Value Area but not at edges
        else:
            if val < current_price < poc:
                score = 1.0
                reason = "In Value Area (Low -> POC)"
            elif poc < current_price < vah:
                score = -1.0
                reason = "In Value Area (POC -> High)"
                
        return score, reason
