import pandas as pd
from datetime import datetime, timedelta
from types import SimpleNamespace
from src.backtest import Backtester, PortfolioBacktester


class FakeAnalyzer:
    def __init__(self):
        self.called = 0

    def analyze_spot(self, symbol, candles):
        # Return ENTRY signal only on first call to open a position
        self.called += 1
        if self.called == 1:
            return SimpleNamespace(action="ENTRY", details={})
        return None


def make_uptrend_df(n=80, start=100.0, step=0.3):
    ts0 = datetime.utcnow() - timedelta(hours=n)
    rows = []
    price = start
    for i in range(n):
        t = ts0 + timedelta(hours=i)
        open_ = price
        close = price + step
        high = max(open_, close) + 0.1
        low = min(open_, close) - 0.1
        vol = 10 + i * 0.01
        rows.append([t, open_, high, low, close, vol])
        price = close
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


def test_backtester_runs_and_records_trades(monkeypatch):
    df = make_uptrend_df()
    bt = Backtester("AAA/USDT", "1h", initial_balance=1000.0)
    # Inject fake analyzer
    bt.analyzer = FakeAnalyzer()

    stats, trades, equity = bt.run(df)
    assert isinstance(stats, dict)
    # Ensure we have at least attempted to trade
    assert "total_trades" in stats
    assert stats["final_balance"] >= 0
    assert isinstance(trades, pd.DataFrame)
    assert isinstance(equity, pd.DataFrame)


def test_portfolio_backtester_on_dfs(monkeypatch):
    symbols = ["AAA/USDT", "BBB/USDT"]
    df = make_uptrend_df()
    pbt = PortfolioBacktester(symbols, "1h", initial_balance=1000.0)
    # Replace analyzers for each backtester
    for bt in pbt.backtesters.values():
        bt.analyzer = FakeAnalyzer()

    stats, all_stats, combined = pbt.run_on_dfs({s: df for s in symbols})
    assert "final_balance" in stats
    assert len(all_stats) == 2
    assert not combined.empty
