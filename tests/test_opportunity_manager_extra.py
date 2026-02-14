from types import SimpleNamespace
from time import time
from src.strategies.opportunity_manager import OpportunityManager


def make_signal(symbol, score, action="ENTRY"):
    return SimpleNamespace(symbol=symbol, score=score, action=action, details={})


def test_swap_locked_override_allows_swap():
    om = OpportunityManager(min_score_diff=5.0)
    now = time()
    portfolio = {
        "AAA/USDT": {"timestamp": now, "quantity": 1.0, "entry_price": 100.0}
    }
    # Locked because timestamp ~ now and min_hold_time default is 3600s
    signals = [
        make_signal("AAA/USDT", 5.0),                # existing low score
        make_signal("ZZZ/USDT", 30.5),               # candidate high score -> diff 25.5 >= 20 override
    ]
    res = om.check_for_swap_opportunity(portfolio, signals)
    assert res is not None
    assert res["action"] == "SWAP"
    assert res["sell_symbol"] == "AAA/USDT"
    assert res["buy_signal"].symbol == "ZZZ/USDT"


def test_bnb_protection_results_none():
    om = OpportunityManager()
    now = time()
    portfolio = {"BNB/USDT": {"timestamp": now, "quantity": 1.0, "entry_price": 300.0}}
    signals = [make_signal("BNB/USDT", 3.0), make_signal("AAA/USDT", 10.0)]
    res = om.check_for_swap_opportunity(portfolio, signals)
    assert res is None


def test_analyze_swap_status_locked_hold_when_below_threshold():
    om = OpportunityManager(min_score_diff=5.0)
    now = time()
    portfolio = {"AAA/USDT": {"timestamp": now, "quantity": 1.0, "entry_price": 100.0}}
    signals = [make_signal("AAA/USDT", 5.0), make_signal("BBB/USDT", 20.0)]  # diff 15 < 20 lock break
    report = om.analyze_swap_status(portfolio, signals)
    assert report["action"] == "HOLD"
    assert report["reason"] == "ASSET_LOCKED_MIN_HOLD_TIME"
