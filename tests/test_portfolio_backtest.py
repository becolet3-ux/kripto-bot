import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtest import PortfolioBacktester


def make_df(n=80, drift=0.1):
    base_time = datetime.utcnow() - timedelta(hours=n)
    ts = [base_time + timedelta(hours=i) for i in range(n)]
    price = 100 + np.cumsum(np.full(n, drift))
    high = price * 1.005
    low = price * 0.995
    openp = price * 0.999
    vol = np.full(n, 1000.0)
    df = pd.DataFrame(
        {"timestamp": ts, "open": openp, "high": high, "low": low, "close": price, "volume": vol}
    )
    return df


def test_portfolio_backtester_on_synthetic_data():
    symbols = ["AAA/USDT", "BBB/USDT"]
    pbt = PortfolioBacktester(symbols, timeframe="1h", initial_balance=1000.0)
    df_map = {
        "AAA/USDT": make_df(80, drift=0.2),
        "BBB/USDT": make_df(80, drift=0.05),
    }
    stats, per_symbol, combined = pbt.run_on_dfs(df_map)
    assert "final_balance" in stats
    assert combined["equity"].iloc[-1] > 0
