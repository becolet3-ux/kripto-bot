import sys
import os
import pandas as pd
from src.backtest import Backtester

def main():
    print("=========================================")
    print("   🤖 KriptoBot Backtest System 1.0    ")
    print("=========================================")
    
    symbol_arg = "BTC/USDT"
    days = 30
    exchange_id = "binance"
    
    # Simple CLI args or interactive
    if len(sys.argv) > 1:
        symbol_arg = sys.argv[1]
    if len(sys.argv) > 2:
        days = int(sys.argv[2])
    portfolio_mode = False
    if len(sys.argv) > 3:
        exchange_id = sys.argv[3]
    if len(sys.argv) > 4 and sys.argv[4].lower() == "portfolio":
        portfolio_mode = True
        
    print(f"Target: {symbol_arg}")
    print(f"Period: {days} Days")
    print(f"Exchange: {exchange_id}")
    print("-----------------------------------------")
    
    try:
        symbols = [s.strip() for s in symbol_arg.split(",")]
        aggregate = []
        if portfolio_mode and len(symbols) > 1:
            from src.backtest import PortfolioBacktester
            print(f"\n=== Portfolio Mode ===")
            df_map = {}
            for symbol in symbols:
                bt_tmp = Backtester(symbol, timeframe='1h', initial_balance=1000.0, exchange_id=exchange_id)
                df = bt_tmp.fetch_data(days=days)
                if df.empty:
                    print(f"❌ No data fetched for {symbol}. Skipping.")
                    continue
                df_map[symbol] = df
            if not df_map:
                print("❌ No data. Exiting.")
                return
            pbt = PortfolioBacktester(symbols, timeframe='1h', initial_balance=1000.0, exchange_id=exchange_id)
            pstats, per_symbol_stats, combined_equity = pbt.run_on_dfs(df_map)
            print("\n📊 PORTFOLIO RESULTS")
            print("-----------------------------------------")
            print(f"Initial Balance: ${pstats['initial_balance']:.2f}")
            print(f"Final Balance:   ${pstats['final_balance']:.2f}")
            print("-----------------------------------------")
            for sym, st in per_symbol_stats.items():
                print(f"{sym} → Final: ${st['final_balance']:.2f} | Return: %{st['total_return_pct']:.2f}")
            return
        else:
            for symbol in symbols:
                print(f"\n=== Running {symbol} ===")
                bt = Backtester(symbol, timeframe='1h', initial_balance=1000.0, exchange_id=exchange_id)
                df = bt.fetch_data(days=days)
                if df.empty:
                    print("❌ No data fetched. Skipping.")
                    continue
                stats, trades_df, equity_df = bt.run(df)
                aggregate.append((symbol, stats, trades_df, equity_df))

        if not aggregate:
            print("❌ No results.")
            return
        print("\n📊 BACKTEST RESULTS")
        print("-----------------------------------------")
        for symbol, stats, trades_df, equity_df in aggregate:
            print(f"Symbol: {symbol}")
            print(f"Initial Balance: ${stats['initial_balance']:.2f}")
            print(f"Final Balance:   ${stats['final_balance']:.2f}")
            print(f"Total Return:    %{stats['total_return_pct']:.2f}")
            print(f"Total Trades:    {stats['total_trades']}")
            print(f"Win Rate:        %{stats['win_rate']:.2f}")
            print(f"Profit Factor:   {stats['profit_factor']:.2f}")
            print(f"Max Drawdown:    %{stats['max_drawdown']:.2f}")
            print("-----------------------------------------")
            if not trades_df.empty:
                os.makedirs("data", exist_ok=True)
                csv_path = f"data/backtest_{symbol.replace('/','_')}.csv"
                trades_df.to_csv(csv_path, index=False)
                print(f"💾 Trade history saved to: {csv_path}")
            
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
