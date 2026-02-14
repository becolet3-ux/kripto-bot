import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtest import Backtester


def make_synthetic_df(n=80):
    base_time = datetime.utcnow() - timedelta(hours=n)
    ts = [base_time + timedelta(hours=i) for i in range(n)]
    price = np.linspace(100, 110, n)
    high = price * 1.01
    low = price * 0.99
    openp = price * 0.999
    vol = np.full(n, 1000.0)
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "open": openp,
            "high": high,
            "low": low,
            "close": price,
            "volume": vol,
        }
    )
    return df


def test_backtester_run_offline_df():
    bt = Backtester("BTC/USDT", timeframe="1h", initial_balance=1000.0)
    df = make_synthetic_df(80)
    stats, trades, equity = bt.run(df)
    assert "initial_balance" in stats
    assert "final_balance" in stats
    assert "total_trades" in stats
    assert isinstance(stats["total_trades"], int)
    assert not equity.empty
