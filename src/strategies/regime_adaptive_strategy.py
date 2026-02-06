from typing import Dict, Any

class RegimeAdaptiveStrategy:
    """
    Provides strategy parameters based on Market Regime.
    Phase 3: Market Regime Detection & Adaptation
    """
    
    @staticmethod
    def get_strategy_params(regime: str) -> Dict[str, Any]:
        """
        Returns strategy parameters optimized for the given regime.
        """
        if regime == 'TRENDING':
            return {
                'description': 'Aggressive Trend Following',
                'trailing_stop_atr_multiplier': 3.0,  # Wider stop to let it run
                'partial_take_profit_pct': 6.0,       # Take profit later
                'position_size_pct': 35.0,            # Larger size
                'leverage_multiplier': 1.5            # Slightly higher leverage allowed (if safe)
            }
        elif regime == 'RANGING':
            return {
                'description': 'Conservative Range Trading',
                'trailing_stop_atr_multiplier': 1.5,  # Tight stop
                'partial_take_profit_pct': 3.0,       # Take profit earlier
                'position_size_pct': 15.0,            # Smaller size
                'leverage_multiplier': 1.0            # Base leverage
            }
        else:
            # Default / Neutral
            return {
                'description': 'Standard Strategy',
                'trailing_stop_atr_multiplier': 2.0,
                'partial_take_profit_pct': 4.0,
                'position_size_pct': 20.0,
                'leverage_multiplier': 1.0
            }
