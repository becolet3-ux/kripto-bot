from typing import Dict, Any, List
import pandas as pd
from src.strategies.breakout_strategy import BreakoutStrategy
from src.strategies.mean_reversion_strategy import MeanReversionStrategy
from src.strategies.momentum_strategy import MomentumStrategy
from src.utils.logger import logger

class StrategyManager:
    """
    Manages multiple sub-strategies and aggregates their signals using a weighted voting system.
    """
    def __init__(self):
        self.strategies = [
            BreakoutStrategy(),
            MeanReversionStrategy(),
            MomentumStrategy()
        ]
        
        # Voting Threshold (e.g., 0.6 means 60% of total weight must agree)
        self.consensus_threshold = 0.6

    def analyze_all(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Runs all strategies and aggregates the results.
        """
        results = []
        total_weight = 0.0
        weighted_score = 0.0 # Entry Score
        
        entry_votes = 0.0
        
        details = {}
        
        for strategy in self.strategies:
            res = strategy.analyze(df)
            results.append(res)
            
            w = strategy.weight
            total_weight += w
            
            details[strategy.name] = res
            
            if res['action'] == "ENTRY":
                entry_votes += w
                weighted_score += res['score'] * w # Weighted average of scores? Or additive?
                # Let's keep it simple: Additive weighted score for sorting
            
        # Normalize Entry Votes
        # If total_weight is 1.0, entry_votes is the fraction.
        vote_ratio = entry_votes / total_weight if total_weight > 0 else 0
        
        final_action = "HOLD"
        primary_strategy = None
        
        # Consensus Check
        if vote_ratio >= self.consensus_threshold:
            final_action = "ENTRY"
            
            # Identify which strategy contributed most (highest score)
            best_s_score = -1
            for res in results:
                if res['action'] == "ENTRY" and res['score'] > best_s_score:
                    best_s_score = res['score']
                    primary_strategy = res['strategy']
        
        # If we have a single strong strategy (high score) but not consensus, 
        # maybe we should still allow it? 
        # The prompt says: "Total: 0.7 > 0.66 threshold -> BUY"
        # So strict consensus is required.
        
        return {
            "action": final_action,
            "vote_ratio": vote_ratio,
            "weighted_score": weighted_score,
            "primary_strategy": primary_strategy,
            "strategy_details": details
        }
