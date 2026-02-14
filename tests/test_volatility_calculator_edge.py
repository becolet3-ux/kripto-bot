import pandas as pd
from src.risk.volatility_calculator import VolatilityCalculator


def test_calculate_atr_empty():
    df = pd.DataFrame(columns=["high", "low", "close"])
    atr = VolatilityCalculator.calculate_atr(df)
    assert atr.empty


def test_get_volatility_pct_short_df_and_zero_price():
    # Short df -> returns 0.0
    df = pd.DataFrame({"high": [1], "low": [0.9], "close": [0.95]})
    assert VolatilityCalculator.get_volatility_pct(df, period=14) == 0.0

    # Create a longer df but with last close 0 -> 0.0 volatility
    df2 = pd.DataFrame({
        "high": [1.0]*20,
        "low": [0.9]*20,
        "close": [1.0]*19 + [0.0],
    })
    assert VolatilityCalculator.get_volatility_pct(df2, period=14) == 0.0
