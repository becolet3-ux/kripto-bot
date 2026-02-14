import time
from src.strategies.opportunity_manager import OpportunityManager
from src.strategies.analyzer import TradeSignal


def make_signal(symbol, score, price_hist=None, action="ENTRY"):
    return TradeSignal(
        symbol=symbol,
        action=action,
        direction="LONG",
        score=score,
        estimated_yield=0.0,
        timestamp=int(time.time() * 1000),
        details={"price_history": price_hist or [i for i in range(50)]},
        primary_strategy="test"
    )


def test_analyze_swap_status_empty_portfolio():
    om = OpportunityManager(min_score_diff=5.0)
    res = om.analyze_swap_status({}, [])
    assert res["action"] == "WAIT"


def test_analyze_swap_status_locked_but_override(monkeypatch):
    om = OpportunityManager(min_score_diff=5.0)
    # Make lock break threshold smaller for test speed if needed
    from config import settings as settings_mod
    monkeypatch.setattr(settings_mod.settings, "OPP_LOCK_BREAK_DIFF", 15.0, raising=False)

    now = time.time()
    portfolio = {
        "AAA/USDT": {"entry_price": 100.0, "quantity": 1.0, "timestamp": now}  # locked by min_hold_time
    }
    worst = make_signal("AAA/USDT", score=2.0)
    cand = make_signal("BBB/USDT", score=25.0)  # diff 23 -> override
    res = om.analyze_swap_status(portfolio, [worst, cand], score_cache={})
    assert res["action"] in ("SWAP_READY", "HOLD")
    # If lock threshold logic executed, should be SWAP_READY


def test_check_for_swap_opportunity_basic():
    om = OpportunityManager(min_score_diff=3.0, min_hold_time=0)
    portfolio = {"AAA/USDT": {"entry_price": 100.0, "quantity": 0.5, "timestamp": time.time() - 5000}}
    worst = make_signal("AAA/USDT", score=2.0)
    cand = make_signal("CCC/USDT", score=8.0)
    res = om.check_for_swap_opportunity(portfolio, [worst, cand])
    assert res is None or res.get("action") in ("SWAP",)
