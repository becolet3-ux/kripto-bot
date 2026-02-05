import json
import ccxt
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

def analyze():
    state_file = "data/bot_state.json"
    if not os.path.exists(state_file):
        print("❌ State file not found!")
        return

    with open(state_file, 'r') as f:
        state = json.load(f)

    positions = state.get('paper_positions', {})
    stats = state.get('stats', {})

    print("\n📊 --- GERÇEKLEŞEN (Kapanan İşlemler) ---")
    print(f"Toplam İşlem: {stats.get('trades', 0)}")
    print(f"Kazanılan: {stats.get('wins', 0)}")
    print(f"Kaybedilen: {stats.get('losses', 0)}")
    print(f"Toplam PnL (Realized): %{stats.get('total_pnl_pct', 0.0):.2f}")
    
    if stats.get('trades', 0) > 0:
        avg_pnl = stats.get('total_pnl_pct', 0.0) / stats.get('trades', 0)
        print(f"Ortalama İşlem Başı PnL: %{avg_pnl:.2f}")

    print("\n📈 --- BEKLEYEN (Açık Pozisyonlar) ---")
    if not positions:
        print("Açık pozisyon yok.")
        return

    exchange = ccxt.binance()
    total_unrealized_pnl = 0.0
    
    print(f"{'COIN':<10} {'GİRİŞ ($)':<12} {'GÜNCEL ($)':<12} {'DURUM (%)':<10}")
    print("-" * 50)

    for symbol, entry_price in positions.items():
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = float(ticker['last'])
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            total_unrealized_pnl += pnl_pct
            
            pnl_str = f"%{pnl_pct:.2f}"
            print(f"{symbol:<10} {entry_price:<12.4f} {current_price:<12.4f} {pnl_str:<10}")
        except Exception as e:
            print(f"{symbol:<10} {entry_price:<12.4f} {'ERROR':<12} {str(e)}")

    print("-" * 50)
    print(f"Toplam Bekleyen PnL: %{total_unrealized_pnl:.2f}")
    avg_unrealized = total_unrealized_pnl / len(positions) if positions else 0
    print(f"Ortalama Bekleyen PnL: %{avg_unrealized:.2f}")

if __name__ == "__main__":
    analyze()
