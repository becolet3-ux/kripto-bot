import pandas as pd
from types import SimpleNamespace
from src.strategies.strategy_manager import StrategyManager


class FakeStrategy:
    def __init__(self, name, weight, action, score):
        self.name = name
        self.weight = weight
        self._action = action
        self._score = score

    def analyze(self, df):
        return {"strategy": self.name, "action": self._action, "score": self._score}


def make_df(n=30):
    import numpy as np
    import datetime as dt
    base = dt.datetime.utcnow()
    ts = [base] * n
    price = 100 + np.arange(n) * 0.1
    df = pd.DataFrame({"timestamp": ts, "open": price, "high": price * 1.01, "low": price * 0.99, "close": price, "volume": 1000})
    return df


def test_strategy_manager_consensus_entry_without_mtf():
    df = make_df()
    sm = StrategyManager()
    # Two strategies vote ENTRY with weights totaling > threshold, one HOLD
    sm.strategies = [
        FakeStrategy("S1", 0.4, "ENTRY", 0.7),
        FakeStrategy("S2", 0.3, "ENTRY", 0.6),
        FakeStrategy("S3", 0.3, "HOLD", 0.0),
    ]
    res = sm.analyze_all(df, "AAA/USDT", exchange=None)
    assert res["action"] in ("ENTRY", "HOLD")
    assert res["vote_ratio"] >= 0.7  # 0.4 + 0.3
    if res["action"] == "ENTRY":
        assert res["weighted_score"] >= 0.6


def test_strategy_manager_mtf_blocks_entry(monkeypatch):
    df = make_df()
    sm = StrategyManager()
    sm.strategies = [
        FakeStrategy("S1", 0.6, "ENTRY", 0.7),
        FakeStrategy("S2", 0.4, "HOLD", 0.0),
    ]

    def fake_mtf(symbol, exchange):
        return {"consensus": False, "blocking_reason": "counter_trend_4h"}

    # Patch the module-level function used inside StrategyManager
    import src.strategies.strategy_manager as smod
    monkeypatch.setattr(smod, "multi_timeframe_analyzer", fake_mtf)

    fake_exchange = SimpleNamespace()
    res = sm.analyze_all(df, "AAA/USDT", exchange=fake_exchange)
    assert res["action"] == "HOLD"
    assert res["strategy_details"].get("mtf_analysis", {}).get("consensus") is False

