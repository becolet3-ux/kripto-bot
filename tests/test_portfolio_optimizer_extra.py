import pandas as pd
import numpy as np
from src.risk.portfolio_optimizer import PortfolioOptimizer


def test_calculate_correlation_matrix_and_diversification_score():
    po = PortfolioOptimizer(correlation_threshold=0.8)
    idx = pd.date_range("2024-01-01", periods=50, freq="H")
    a = pd.Series(np.linspace(100, 150, 50), index=idx)
    b = a * 1.5  # perfectly correlated
    mat = po.calculate_correlation_matrix({"AAA": a, "BBB": b})
    assert not mat.empty
    assert "AAA" in mat and "BBB" in mat
    score = po.get_diversification_score({"AAA": 0.5, "BBB": 0.5}, mat)
    assert 0.0 <= score <= 100.0


def test_check_correlation_risk_detects_high_corr():
    po = PortfolioOptimizer(correlation_threshold=0.5)
    idx = pd.date_range("2024-01-01", periods=60, freq="H")
    base = pd.Series(np.linspace(10, 20, 60), index=idx)
    # Candidate is almost identical -> high correlation ~1
    candidate = base + 0.001

    res = po.check_correlation_risk({"AAA": base}, "ZZZ", candidate)
    assert res["is_safe"] == False
    assert res["max_correlation"] > 0.9
