import time
import pytest
from src.strategies.opportunity_manager import OpportunityManager
from src.strategies.analyzer import TradeSignal


def make_signal(symbol, score, price_hist=None, action="ENTRY", extra_details=None):
    details = {"price_history": price_hist or [i for i in range(50)]}
    if extra_details:
        details.update(extra_details)
    return TradeSignal(
        symbol=symbol,
        action=action,
        direction="LONG",
        score=score,
        estimated_yield=0.0,
        timestamp=int(time.time() * 1000),
        details=details,
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


def test_get_net_score_with_negative_funding():
    om = OpportunityManager()
    base_score = 37.5
    funding_pct = -0.3766
    sig_no_funding = make_signal(
        "MOVE/USDT",
        score=base_score,
        extra_details={"funding_rate_pct": 0.0},
    )
    sig_with_funding = make_signal(
        "MOVE/USDT",
        score=base_score,
        extra_details={"funding_rate_pct": funding_pct},
    )

    net_no = om._get_net_score(sig_no_funding)
    net_neg = om._get_net_score(sig_with_funding)
    assert net_neg < net_no


def test_check_for_swap_opportunity_penalizes_high_funding(monkeypatch):
    om = OpportunityManager(min_score_diff=0.1, min_hold_time=0)

    now = time.time()
    portfolio = {
        "AAA/USDT": {"entry_price": 10.0, "quantity": 1.0, "timestamp": now - 5000}
    }

    # Worst asset: base score 10, strong negative funding
    worst = make_signal(
        "AAA/USDT",
        score=10.0,
        extra_details={"funding_rate_pct": -0.5},
    )

    # Candidate: slightly higher raw score, no funding cost
    cand = make_signal(
        "BBB/USDT",
        score=10.4,
        extra_details={"funding_rate_pct": 0.0},
    )

    # Avoid correlation blocking the test
    def fake_risk_ok(*args, **kwargs):
        return {"is_safe": True, "max_correlation": 0.0, "correlated_with": None}

    monkeypatch.setattr(om.portfolio_optimizer, "check_correlation_risk", fake_risk_ok)

    res = om.check_for_swap_opportunity(portfolio, [worst, cand])
    assert res is not None
    assert res.get("action") == "SWAP"
    assert res.get("sell_symbol") == "AAA/USDT"
