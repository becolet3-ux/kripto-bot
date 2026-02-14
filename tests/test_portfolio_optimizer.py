import pandas as pd
import numpy as np
from src.risk.portfolio_optimizer import PortfolioOptimizer


def s(values, start=0):
    return pd.Series(values, index=pd.RangeIndex(start, start + len(values)))


def test_empty_portfolio_is_safe():
    opt = PortfolioOptimizer()
    res = opt.check_correlation_risk({}, "BTC/USDT", s(np.arange(10)))
    assert res["is_safe"] == True
    assert res["max_correlation"] == 0.0


def test_insufficient_history_returns_safe():
    opt = PortfolioOptimizer()
    port = {"AAA/USDT": s(np.arange(20))}
    res = opt.check_correlation_risk(port, "BBB/USDT", s(np.arange(20)))
    assert res["is_safe"] == True
    assert "Insufficient" in res["reason"]


def test_high_correlation_blocked():
    opt = PortfolioOptimizer()
    x = np.arange(100)
    port = {"AAA/USDT": s(x)}
    candidate = s(x * 2)  # perfectly correlated
    res = opt.check_correlation_risk(port, "BBB/USDT", candidate)
    assert res["is_safe"] == False
    assert res["max_correlation"] >= 0.9


def test_candidate_dropped_during_alignment():
    opt = PortfolioOptimizer()
    port = {"AAA/USDT": s(np.arange(50), start=0)}
    candidate = s(np.arange(50), start=100)  # no overlap -> dropped
    res = opt.check_correlation_risk(port, "BBB/USDT", candidate)
    assert res["is_safe"] == True
    assert ("Candidate" in res["reason"]) or ("Insufficient" in res["reason"])


def test_low_correlation_safe():
    opt = PortfolioOptimizer()
    x = np.arange(100)
    zigzag = np.array([1 if i % 2 == 0 else -1 for i in range(100)])
    port = {"AAA/USDT": s(x)}
    res = opt.check_correlation_risk(port, "BBB/USDT", s(zigzag))
    assert res["is_safe"] == True
