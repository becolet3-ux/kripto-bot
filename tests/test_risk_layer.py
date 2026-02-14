import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import settings
from src.risk.volatility_calculator import VolatilityCalculator
from src.risk.position_sizer import PositionSizer


def make_df(n=50, base=100.0, step=0.1):
    base_time = datetime.utcnow() - timedelta(minutes=n)
    ts = [base_time + timedelta(minutes=i) for i in range(n)]
    prices = base + np.arange(n) * step
    high = prices * 1.005
    low = prices * 0.995
    openp = prices * 0.999
    vol = np.full(n, 1000.0)
    df = pd.DataFrame(
        {"timestamp": ts, "open": openp, "high": high, "low": low, "close": prices, "volume": vol}
    )
    return df


def test_volatility_calculator_pct_low():
    df = make_df(60, base=100.0, step=0.01)  # çok düşük oynaklık
    vol_pct = VolatilityCalculator.get_volatility_pct(df, period=14)
    assert vol_pct >= 0.0
    assert vol_pct < settings.VOLATILITY_LOW_THRESHOLD


def test_volatility_calculator_pct_high():
    # yapay yüksek oynaklık: high-low farkını büyüt
    df = make_df(60, base=100.0, step=0.5)
    df["high"] = df["close"] * 1.05
    df["low"] = df["close"] * 0.95
    vol_pct = VolatilityCalculator.get_volatility_pct(df, period=14)
    assert vol_pct > settings.VOLATILITY_HIGH_THRESHOLD


def test_position_sizer_low_medium_high_and_regime():
    sizer = PositionSizer()
    balance = 1000.0
    symbol = "AAA/USDT"

    # LOW vol
    params_low = sizer._get_params(settings.VOLATILITY_LOW_THRESHOLD - 0.1, balance, symbol, "NEUTRAL")
    assert params_low["risk_level"] == "LOW"
    assert params_low["leverage"] == settings.LEVERAGE_LOW_VOL
    assert abs(params_low["position_cost_usdt"] - balance * (settings.POS_SIZE_LOW_VOL_PCT / 100)) < 1e-6

    # HIGH vol
    params_high = sizer._get_params(settings.VOLATILITY_HIGH_THRESHOLD + 0.1, balance, symbol, "NEUTRAL")
    assert params_high["risk_level"] == "HIGH"
    assert params_high["leverage"] == settings.LEVERAGE_HIGH_VOL
    assert abs(params_high["position_cost_usdt"] - balance * (settings.POS_SIZE_HIGH_VOL_PCT / 100)) < 1e-6

    # MEDIUM vol
    mid = (settings.VOLATILITY_LOW_THRESHOLD + settings.VOLATILITY_HIGH_THRESHOLD) / 2.0
    params_med = sizer._get_params(mid, balance, symbol, "NEUTRAL")
    assert params_med["risk_level"] == "MEDIUM"
    assert params_med["leverage"] == settings.LEVERAGE_MED_VOL

    # TRENDING regime should bump size to at least 35% unless HIGH risk
    params_trend = sizer._get_params(settings.VOLATILITY_LOW_THRESHOLD + 0.1, balance, symbol, "TRENDING")
    assert params_trend["risk_level"] != "HIGH"
    assert params_trend["position_cost_usdt"] >= balance * 0.35

    # RANGING regime should cap at 15%
    params_range = sizer._get_params(settings.VOLATILITY_LOW_THRESHOLD + 0.1, balance, symbol, "RANGING")
    assert params_range["position_cost_usdt"] <= balance * 0.15

