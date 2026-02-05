import sys
import os
import pandas as pd
from src.backtest import Backtester

def main():
    print("=========================================")
    print("   🤖 KriptoBot Backtest System 1.0    ")
    print("=========================================")
    
    symbol = "BTC/USDT"
    days = 30
    
    # Simple CLI args or interactive
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    if len(sys.argv) > 2:
        days = int(sys.argv[2])
        
    print(f"Target: {symbol}")
    print(f"Period: {days} Days")
    print("-----------------------------------------")
    
    try:
        bt = Backtester(symbol, timeframe='1h', initial_balance=1000.0)
        
        # 1. Fetch Data
        df = bt.fetch_data(days=days)
        
        if df.empty:
            print("❌ No data fetched. Exiting.")
            return

        # 2. Run Simulation
        stats, trades_df, equity_df = bt.run(df)
        
        # 3. Display Results
        print("\n📊 BACKTEST RESULTS")
        print("-----------------------------------------")
        print(f"Initial Balance: ${stats['initial_balance']:.2f}")
        print(f"Final Balance:   ${stats['final_balance']:.2f}")
        print(f"Total Return:    %{stats['total_return_pct']:.2f}")
        print(f"Total Trades:    {stats['total_trades']}")
        print(f"Win Rate:        %{stats['win_rate']:.2f}")
        print(f"Profit Factor:   {stats['profit_factor']:.2f}")
        print(f"Max Drawdown:    %{stats['max_drawdown']:.2f}")
        print("-----------------------------------------")
        
        # 4. Save Trades to CSV
        if not trades_df.empty:
            csv_path = f"data/backtest_{symbol.replace('/','_')}.csv"
            trades_df.to_csv(csv_path, index=False)
            print(f"💾 Trade history saved to: {csv_path}")
            
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
