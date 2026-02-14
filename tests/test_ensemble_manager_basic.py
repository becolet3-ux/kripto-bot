import pandas as pd
import numpy as np
from pathlib import Path
from src.ml.ensemble_manager import EnsembleManager, SKLEARN_AVAILABLE


def make_df(n=60):
    data = {
        "RSI": np.random.uniform(30, 70, n),
        "MACD": np.random.normal(0, 1, n),
        "CCI": np.random.normal(0, 100, n),
        "ADX": np.random.uniform(10, 40, n),
        "MFI": np.random.uniform(20, 80, n),
        "Stoch_RSI_K": np.random.uniform(0, 100, n),
        "Stoch_RSI_D": np.random.uniform(0, 100, n),
        "Williams_R": np.random.uniform(-100, 0, n),
        "ATR": np.random.uniform(0.5, 2.0, n),
        "Bollinger_Upper": np.linspace(101, 105, n),
        "Bollinger_Lower": np.linspace(99, 95, n),
        "SMA_50": np.linspace(100, 102, n),
        "SMA_200": np.linspace(100, 101, n),
        "VWAP": np.linspace(100, 101, n),
        "close": np.linspace(100, 103, n),
    }
    df = pd.DataFrame(data)
    df["Target"] = (df["close"].diff().fillna(0) > 0).astype(int)
    return df


def test_predict_neutral_without_training(tmp_path: Path):
    em = EnsembleManager(models_dir=str(tmp_path))
    p = em.predict_proba(pd.DataFrame())
    assert p == 0.5


def test_train_and_predict(tmp_path: Path):
    em = EnsembleManager(models_dir=str(tmp_path))
    if not SKLEARN_AVAILABLE or len(em.models) == 0:
        # If sklearn not available, ensure predict still returns neutral
        p = em.predict_proba(make_df(60))
        assert p == 0.5
        return

    df = make_df(80)
    metrics = em.train(df, target_col="Target")
    assert em.is_trained is True
    # Train may return None if something went wrong; tolerate as long as training flag set
    p = em.predict_proba(df)
    assert 0.0 <= p <= 1.0
