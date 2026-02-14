import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import List, Dict
from src.strategies.analyzer import MarketAnalyzer, TradeSignal

class Backtester:
    def __init__(self, symbol: str, timeframe: str = '1h', initial_balance: float = 1000.0, exchange_id: str = 'binance'):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = None # {price, amount, time}
        self.trades = []
        self.equity_curve = []
        self.analyzer = MarketAnalyzer()
        self.exchange_id = exchange_id
        self.atr_mult = 2.0
        self.take_profit_pct = 10.0
        
        # Simulation settings
        self.commission = 0.001 # 0.1%
        self.slippage = 0.001 # 0.1%
        
    def fetch_data(self, days: int = 30):
        """Fetches historical data from Binance (Public API)"""
        print(f"⏳ Fetching {days} days of history for {self.symbol} via {self.exchange_id}...")
        if not hasattr(ccxt, self.exchange_id):
            raise ValueError(f"Unsupported exchange_id: {self.exchange_id}")
        exchange = getattr(ccxt, self.exchange_id)()
        since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
        all_candles = []
        
        while since < exchange.milliseconds():
            candles = exchange.fetch_ohlcv(self.symbol, self.timeframe, since, limit=1000)
            if not candles:
                break
            
            since = candles[-1][0] + 1
            all_candles.extend(candles)
            time.sleep(0.5) # Rate limit
            
        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        print(f"✅ Loaded {len(df)} candles.")
        return df

    def run(self, df: pd.DataFrame):
        """Runs the backtest loop"""
        print("🚀 Starting Backtest...")
        
        # Pre-calculate indicators for speed (vectorized)
        # However, our analyzer calculates them on the fly per window. 
        # For strict correctness with the live bot, we should loop.
        # But for speed, we might want to pre-calc. 
        # Let's stick to looping for accuracy with current bot logic.
        
        window_size = 50 # Analyzer uses last 50 candles
        
        for i in range(window_size, len(df)):
            # Create a window of candles (list of lists as expected by analyzer)
            # We need to convert DataFrame row to list format: [ts, o, h, l, c, v]
            window_df = df.iloc[i-window_size:i+1] # Include current candle as "closed" or "forming"
            
            # Convert to list of lists (timestamp needs to be int ms for analyzer)
            current_candles = []
            for _, row in window_df.iterrows():
                current_candles.append([
                    int(row['timestamp'].timestamp() * 1000),
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ])
                
            current_price = current_candles[-1][4]
            current_time = window_df.iloc[-1]['timestamp']
            
            # Analyze
            signal = self.analyzer.analyze_spot(self.symbol, current_candles)
            
            # Execute Logic
            if signal:
                self._process_signal(signal, current_price, current_time, window_df)
            
            # Stop Loss / Take Profit Logic (if holding)
            if self.position:
                self._check_risk_management(current_price, current_time, window_df)
                
            # Record Equity
            total_value = self.balance
            if self.position:
                total_value = self.position['amount'] * current_price
            self.equity_curve.append({'time': current_time, 'equity': total_value})

        self._finalize()
        return self.get_results()

    def _process_signal(self, signal: TradeSignal, price: float, time: datetime, window_df: pd.DataFrame):
        if signal.action == "ENTRY" and not self.position:
            # Buy
            entry_price = price * (1 + self.slippage)
            amount = (self.balance * 0.99) / entry_price # Use 99% of balance
            cost = amount * entry_price
            fee = cost * self.commission
            
            self.balance -= (cost + fee)
            atr = self._calc_atr(window_df)
            trail = entry_price - (atr * self.atr_mult) if atr > 0 else entry_price * 0.95
            self.position = {
                'entry_price': entry_price,
                'amount': amount,
                'entry_time': time,
                'features': signal.details,
                'trail_stop': trail,
                'max_price': entry_price
            }
            
            self.trades.append({
                'type': 'BUY',
                'price': entry_price,
                'time': time,
                'reason': 'SIGNAL'
            })
            
        elif signal.action == "EXIT" and self.position:
            # Sell
            self._close_position(price, time, 'SIGNAL')

    def _check_risk_management(self, price: float, time: datetime, window_df: pd.DataFrame):
        if not self.position:
            return
            
        entry_price = self.position['entry_price']
        pnl_pct = ((price - entry_price) / entry_price) * 100
        atr = self._calc_atr(window_df)
        if atr > 0:
            new_trail = price - (atr * self.atr_mult)
            if new_trail > self.position['trail_stop']:
                self.position['trail_stop'] = new_trail
        if price > self.position['max_price']:
            self.position['max_price'] = price
        if price <= self.position['trail_stop']:
            self._close_position(price, time, 'TRAILING_STOP')
            return
        if pnl_pct >= self.take_profit_pct:
            self._close_position(price, time, 'TAKE_PROFIT')

    def _close_position(self, price: float, time: datetime, reason: str):
        if not self.position:
            return
            
        exit_price = price * (1 - self.slippage)
        amount = self.position['amount']
        revenue = amount * exit_price
        fee = revenue * self.commission
        
        self.balance += (revenue - fee)
        
        # Calculate PnL
        entry_price = self.position['entry_price']
        pnl = revenue - fee - (amount * entry_price) # Net PnL value
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 # Gross PnL %
        
        self.trades.append({
            'type': 'SELL',
            'price': exit_price,
            'time': time,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        })
        
        self.position = None

    def _finalize(self):
        # Close any open position at end
        if self.position:
            last_price = self.equity_curve[-1]['equity'] / self.position['amount'] # Approx
            self._close_position(last_price, self.equity_curve[-1]['time'], 'END_OF_TEST')

    def get_results(self):
        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)
        
        # Calculate Profit Factor
        gross_profit = 0
        gross_loss = 0
        if not df_trades.empty:
            gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
            
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

        stats = {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_return_pct': ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            'total_trades': len(df_trades[df_trades['type'] == 'SELL']) if not df_trades.empty else 0,
            'win_rate': 0,
            'profit_factor': profit_factor,
            'max_drawdown': 0
        }
        
        if not df_trades.empty:
            wins = len(df_trades[(df_trades['type'] == 'SELL') & (df_trades['pnl'] > 0)])
            stats['win_rate'] = (wins / stats['total_trades']) * 100 if stats['total_trades'] > 0 else 0
            
        if not df_equity.empty:
            df_equity['peak'] = df_equity['equity'].cummax()
            df_equity['drawdown'] = (df_equity['equity'] - df_equity['peak']) / df_equity['peak']
            stats['max_drawdown'] = df_equity['drawdown'].min() * 100
            
        return stats, df_trades, df_equity

    def _calc_atr(self, window_df: pd.DataFrame, period: int = 14) -> float:
        if window_df.empty or len(window_df) < period:
            return 0.0
        h = window_df['high']
        l = window_df['low']
        c = window_df['close']
        tr1 = h - l
        tr2 = (h - c.shift()).abs()
        tr3 = (l - c.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        return float(atr) if pd.notnull(atr) else 0.0

class PortfolioBacktester:
    def __init__(self, symbols: list[str], timeframe: str = '1h', initial_balance: float = 1000.0, exchange_id: str = 'binance'):
        self.symbols = symbols
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.exchange_id = exchange_id
        self.backtesters = {s: Backtester(s, timeframe, initial_balance / len(symbols), exchange_id) for s in symbols}

    def run_on_dfs(self, df_map: Dict[str, pd.DataFrame]):
        total_equity = []
        all_stats = {}
        for s, bt in self.backtesters.items():
            df = df_map.get(s)
            stats, trades, equity = bt.run(df)
            all_stats[s] = stats
            total_equity.append(equity['equity'])
        combined = pd.concat(total_equity, axis=1).sum(axis=1).to_frame('equity')
        stats = {
            'initial_balance': self.initial_balance,
            'final_balance': float(combined['equity'].iloc[-1]),
        }
        return stats, all_stats, combined

if __name__ == "__main__":
    # Test Run
    bt = Backtester("BTC/USDT", "1h")
    df = bt.fetch_data(days=7)
    stats, trades, equity = bt.run(df)
    print("\n=== Backtest Results ===")
    print(f"Initial Balance: ${bt.initial_balance}")
    print(f"Final Balance: ${stats['final_balance']:.2f}")
    print(f"Return: %{stats['total_return_pct']:.2f}")
    print(f"Trades: {stats['total_trades']}")
    print(f"Win Rate: %{stats['win_rate']:.1f}")
    print(f"Max Drawdown: %{stats['max_drawdown']:.2f}")
