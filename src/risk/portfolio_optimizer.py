import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from src.utils.logger import logger

class PortfolioOptimizer:
    """
    Manages portfolio risk through diversification and correlation analysis.
    Implements Modern Portfolio Theory (MPT) concepts to reduce risk.
    """
    
    def __init__(self, correlation_threshold: float = 0.75):
        """
        Args:
            correlation_threshold: Max allowed correlation between assets (0.0 to 1.0).
                                 If a new asset has >0.75 correlation with any existing asset,
                                 it might be rejected or penalized.
        """
        self.correlation_threshold = correlation_threshold

    def calculate_correlation_matrix(self, price_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Calculates correlation matrix for given price series.
        Args:
            price_data: Dictionary mapping symbols to their close price Series.
                       Ensure all Series have the same index (timestamp).
        """
        if not price_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(price_data)
        return df.corr()

    def check_correlation_risk(self, 
                             portfolio_prices: Dict[str, pd.Series], 
                             candidate_symbol: str, 
                             candidate_prices: pd.Series) -> Dict:
        """
        Checks if adding a candidate symbol would increase portfolio risk 
        due to high correlation with existing assets.
        
        Args:
            portfolio_prices: Dict of {symbol: price_series} for current holdings.
            candidate_symbol: The symbol we want to buy.
            candidate_prices: Price series for the candidate.
            
        Returns:
            Dict containing risk analysis results.
        """
        if not portfolio_prices:
            return {
                "is_safe": True, 
                "max_correlation": 0.0, 
                "correlated_with": None,
                "reason": "Portfolio is empty"
            }
            
        # Combine data
        data = portfolio_prices.copy()
        data[candidate_symbol] = candidate_prices
        
        # Create DataFrame and align timestamps (inner join by default)
        # We need to ensure we are comparing same timeframes
        try:
            df = pd.DataFrame(data).dropna()
        except Exception as e:
            logger.error(f"Error constructing correlation dataframe: {e}")
            return {"is_safe": True, "max_correlation": 0.0, "reason": "Data error"}
        
        if len(df) < 30: # Need at least 30 common data points for valid correlation
             return {
                 "is_safe": True, 
                 "max_correlation": 0.0, 
                 "reason": "Insufficient common history (N<30)"
             }

        # Calculate Correlation Matrix
        corr_matrix = df.corr()
        
        # Get correlations for the candidate symbol
        if candidate_symbol not in corr_matrix:
             return {"is_safe": True, "max_correlation": 0.0, "reason": "Candidate dropped during alignment"}

        candidate_corrs = corr_matrix[candidate_symbol].drop(candidate_symbol)
        
        if candidate_corrs.empty:
             return {"is_safe": True, "max_correlation": 0.0, "reason": "No overlap"}

        max_corr = candidate_corrs.max()
        most_correlated = candidate_corrs.idxmax()
        
        is_safe = max_corr < self.correlation_threshold
        
        return {
            "is_safe": is_safe,
            "max_correlation": float(max_corr),
            "correlated_with": most_correlated,
            "reason": f"Max correlation {max_corr:.2f} with {most_correlated}"
        }

    def get_diversification_score(self, portfolio_weights: Dict[str, float], correlation_matrix: pd.DataFrame) -> float:
        """
        Calculates a diversification score (0-100).
        Higher is better. Based on Portfolio Variance.
        """
        # Placeholder for more advanced calculation
        # Currently just returns average correlation (inverted)
        if correlation_matrix.empty:
            return 100.0
            
        avg_corr = correlation_matrix.values.mean()
        # Avg corr usually 0 to 1. 
        # Score = (1 - avg_corr) * 100
        score = (1.0 - avg_corr) * 100
        return max(0.0, min(100.0, score))
