from src.strategies.funding_aware_strategy import FundingAwareStrategy


class DummyFundingLoader:
    def __init__(self, rate):
        self._rate = rate

    def get_funding_rate(self, symbol: str):
        return self._rate


def test_funding_aggressive_long():
    strat = FundingAwareStrategy(DummyFundingLoader(0.0012))  # 0.12%
    res = strat.analyze_funding("BTC/USDT")
    assert res["action"] == "AGGRESSIVE_LONG"
    assert res["score_boost"] >= 2.0


def test_funding_boost_long():
    strat = FundingAwareStrategy(DummyFundingLoader(0.0006))  # 0.06%
    res = strat.analyze_funding("BTC/USDT")
    assert res["action"] == "BOOST_LONG"
    assert res["score_boost"] >= 1.0


def test_funding_ignore_long_negative():
    strat = FundingAwareStrategy(DummyFundingLoader(-0.0001))  # -0.01%
    res = strat.analyze_funding("BTC/USDT")
    assert res["action"] == "IGNORE_LONG"
    assert res["score_boost"] <= -5.0
