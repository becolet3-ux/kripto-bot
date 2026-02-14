import pandas as pd
from src.risk.position_sizer import PositionSizer


def test_calculate_params_from_atr_risk_buckets_and_regime():
    ps = PositionSizer()
    total = 1000.0

    # Low volatility: atr/price = 1% < low threshold (2%)
    low = ps.calculate_params_from_atr("AAA/USDT", atr_value=1.0, price=100.0, total_balance=total, regime="RANGING")
    assert low["risk_level"] == "LOW"
    # Ranging clamps size to <= 15%
    assert low["position_cost_usdt"] <= total * 0.15 + 1e-6

    # Medium volatility: 3% between 2% and 4%
    med = ps.calculate_params_from_atr("BBB/USDT", atr_value=3.0, price=100.0, total_balance=total, regime="TRENDING")
    assert med["risk_level"] == "MEDIUM"
    # Trending boosts to at least 35% if not HIGH risk
    assert med["position_cost_usdt"] >= total * 0.35 - 1e-6

    # High volatility: 5% > 4%
    high = ps.calculate_params_from_atr("CCC/USDT", atr_value=5.0, price=100.0, total_balance=total, regime="TRENDING")
    assert high["risk_level"] == "HIGH"
    # In HIGH risk, regime shouldn't boost above high cap settings
    assert high["position_cost_usdt"] <= total  # sanity


def test_invalid_price_returns_zero():
    ps = PositionSizer()
    res = ps.calculate_params_from_atr("ZZZ/USDT", atr_value=1.0, price=0.0, total_balance=1000.0, regime="NEUTRAL")
    assert res["position_cost_usdt"] == 0.0
    assert res["leverage"] == 1
