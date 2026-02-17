
import re
import sys
import pandas as pd
from datetime import datetime
import requests
import time

# Log dosyasını oku
LOG_FILE = "last_24h_logs.txt"

def analyze_opportunities():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = f.readlines()
    except FileNotFoundError:
        print(f"Log dosyası bulunamadı: {LOG_FILE}")
        return

    signals = []
    current_prices = {}
    
    print("Loglar taranıyor...")
    
    for i, line in enumerate(logs):
        # Fiyat yakala
        price_match = re.search(r'DEBUG: ([A-Z0-9/]+) Last Candle Time:.*?Close:\s*([0-9.]+)', line)
        if price_match:
            sym = price_match.group(1)
            price = float(price_match.group(2))
            current_prices[sym] = price
            
        # Sinyal yakala
        signal_match = re.search(r'Signal Detected for ([A-Z0-9/]+): ENTRY \(Score: ([0-9.]+)\)', line)
        if signal_match:
            symbol = signal_match.group(1)
            score = float(signal_match.group(2))
            entry_price = current_prices.get(symbol, 0)
            
            if entry_price > 0:
                signals.append({
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'score': score,
                    'log_index': i
                })
    
    if not signals:
        print("Loglarda ENTRY sinyali bulunamadı.")
        return

    # Tekrar eden sinyalleri ele
    unique_signals = {}
    for s in signals:
        if s['symbol'] not in unique_signals:
            unique_signals[s['symbol']] = s
            
    final_signals = list(unique_signals.values())
    print(f"Toplam {len(final_signals)} benzersiz fırsat bulundu.")
    
    # Şu anki fiyatları çek (Basit requests ile)
    print("Güncel fiyatlar çekiliyor (Requests)...")
    
    report = []
    trade_size = 20.0
    
    # Binance Public API
    base_url = "https://api.binance.com/api/v3/ticker/price"
    
    for signal in final_signals:
        symbol = signal['symbol']
        clean_symbol = symbol.replace("/", "") # BNB/USDT -> BNBUSDT
        entry_price = signal['entry_price']
        
        try:
            resp = requests.get(f"{base_url}?symbol={clean_symbol}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                current_price = float(data['price'])
                
                # PnL Hesapla
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                leverage = 3
                pnl_leveraged = pnl_pct * leverage
                pnl_net = pnl_leveraged - 0.2
                profit_usd = (trade_size * pnl_net) / 100
                
                report.append({
                    'symbol': symbol,
                    'entry': entry_price,
                    'current': current_price,
                    'raw_change': pnl_pct,
                    'net_pnl_pct': pnl_net,
                    'profit_usd': profit_usd
                })
            else:
                # print(f"Hata {symbol}: {resp.status_code}")
                pass
        except Exception as e:
            # print(f"Exception {symbol}: {e}")
            pass
            
        # Rate limit
        time.sleep(0.1)
                
    
    # Raporu Yazdır
    print("\n--- 100$ SİMÜLASYON RAPORU (Son 24 Saat) ---")
    print(f"Varsayım: 100$ Bakiye, İşlem Başı 20$ (Max 5 İşlem), Kaldıraç 3x\n")
    
    total_usd_gain = 0
    winning_trades = 0
    initial_balance = 100.0
    
    # İlk 5 işlemi al (Zaman sırasına göre)
    executed_trades = report[:5]
    
    for trade in executed_trades:
        status = "✅ KAZANÇ" if trade['profit_usd'] > 0 else "❌ KAYIP"
        if trade['profit_usd'] > 0: winning_trades += 1
        total_usd_gain += trade['profit_usd']
        
        print(f"{status} | {trade['symbol']:<10} | Giriş: {trade['entry']:.4f} -> Güncel: {trade['current']:.4f} | Değişim: %{trade['raw_change']:.2f} | Net Kar: ${trade['profit_usd']:.2f}")
        
    final_balance = initial_balance + total_usd_gain
    if executed_trades:
        roi = ((final_balance - initial_balance) / initial_balance) * 100
    else:
        roi = 0.0
    
    print("-" * 50)
    print(f"Başlangıç Bakiyesi: ${initial_balance:.2f}")
    print(f"Son Bakiye       : ${final_balance:.2f}")
    print(f"Net Değişim      : ${total_usd_gain:.2f} (%{roi:.2f})")
    print(f"Başarı Oranı     : {winning_trades}/{len(executed_trades) if executed_trades else 1}")

if __name__ == "__main__":
    analyze_opportunities()
