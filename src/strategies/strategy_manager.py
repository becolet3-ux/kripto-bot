from typing import Dict, Any, List, Optional
import pandas as pd
from config.settings import settings
from src.strategies.breakout_strategy import BreakoutStrategy
from src.strategies.mean_reversion_strategy import MeanReversionStrategy
from src.strategies.momentum_strategy import MomentumStrategy
from src.strategies.multi_timeframe import multi_timeframe_analyzer
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
        self.consensus_threshold = settings.CONSENSUS_THRESHOLD

    def analyze_all(self, df: pd.DataFrame, symbol: str, exchange: Any = None) -> Dict[str, Any]:
        """
        Runs all strategies and aggregates the results.
        
        Args:
            df (pd.DataFrame): Candle data for the primary timeframe (usually 1h or 15m)
            symbol (str): Trading pair symbol
            exchange (Any, optional): Exchange client for fetching MTF data. Defaults to None.
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
        
        # Normalize Weighted Score
        if entry_votes > 0:
            weighted_score = weighted_score / entry_votes
            
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
        
        # --- Multi-Timeframe Confirmation (MTF) ---
        mtf_result = {}
        
        # Stats tracking
        self.stats = getattr(self, 'stats', {'mtf_checks': 0, 'mtf_consensus': 0, 'mtf_blocks': 0})

        if final_action == "ENTRY" and exchange:
            try:
                self.stats['mtf_checks'] += 1
                # 3-Layer Confirmation (15m, 1h, 4h)
                mtf_result = multi_timeframe_analyzer(symbol, exchange)
                
                # Check for Blocking Condition (e.g., 4H Counter-Trend)
                if not mtf_result.get('consensus', True):
                    final_action = "HOLD"
                    primary_strategy = "blocked_by_mtf"
                    self.stats['mtf_blocks'] += 1
                    logger.log(f"DEBUG: 🚫 {symbol} MTF Block: {mtf_result.get('blocking_reason', 'No consensus')}")
                
                # Check for Consensus Bonus
                elif mtf_result.get('consensus'):
                    self.stats['mtf_consensus'] += 1
                    bonus = mtf_result.get('confidence_multiplier', 1.0)
                    if bonus > 1.0:
                        old_score = weighted_score
                        weighted_score *= bonus
                        logger.log(f"DEBUG: ✨ {symbol} MTF Consensus! Score: {old_score:.2f} -> {weighted_score:.2f}")
                        
                        # YENİ: Final skor kontrolü
                        if weighted_score < 0.60:
                            final_action = "HOLD"
                            primary_strategy = "mtf_score_too_low"
                            logger.log(f"DEBUG: ⚠️ {symbol} MTF bonus sonrası bile yetersiz: {weighted_score:.2f}")
                        
                details['mtf_analysis'] = mtf_result
                
            except Exception as e:
                logger.log(f"❌ MTF Analysis failed for {symbol}: {e}")
        
        return {
            "action": final_action,
            "vote_ratio": vote_ratio,
            "weighted_score": weighted_score,
            "primary_strategy": primary_strategy,
            "strategy_details": details
        }
