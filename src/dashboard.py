import streamlit as st
import json
import pandas as pd
import time
import os
import sys
from collections import deque

# Add project root to path to ensure imports work
sys.path.append(os.getcwd())

import ccxt
import asyncio
from datetime import datetime, timedelta
# from src.collectors.binance_tr_client import BinanceTRClient

# Set page config
st.set_page_config(
    page_title="Kripto Bot Dashboard",
    page_icon="🚀",
    layout="wide"
)

# Constants
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resolve_state_file():
    candidates = []
    env_path = os.getenv("STATE_FILE")
    if env_path:
        candidates.append(env_path)
    candidates.extend([
        "data/bot_state_live.json",
        "data/bot_state.json",
        "bot_state_live.json",
        "bot_state.json",
        "local_backup_data/bot_state_live.json",
        "local_backup_data/bot_state.json"
    ])
    resolved = None
    for candidate in candidates:
        if not candidate:
            continue
        if not os.path.isabs(candidate):
            candidate_path = os.path.join(APP_ROOT, candidate.lstrip("/"))
        else:
            candidate_path = candidate
        if os.path.exists(candidate_path):
            resolved = candidate_path
            break
        if resolved is None:
            resolved = candidate_path
    return resolved

STATE_FILE = resolve_state_file()
LEARNING_FILE = "data/learning_data.json"
LOG_FILE = os.getenv("LOG_FILE", "data/bot_activity.log")

def ensure_state_file(path: str):
    try:
        if not path:
            return
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(path):
            initial = {}
            live_env = os.getenv("LIVE_TRADING")
            if isinstance(live_env, str):
                is_live_flag = live_env.lower() in ("1", "true", "yes", "on")
                initial["is_live"] = is_live_flag
            with open(path, "w") as f:
                json.dump(initial, f)
    except Exception:
        pass

@st.cache_resource
def get_exchange():
    return ccxt.binance()

@st.cache_data(ttl=60)
def get_asset_prices_in_usdt(assets):
    exchange = get_exchange()
    prices = {}
    for asset in assets:
        if asset == 'USDT':
            prices[asset] = 1.0
            continue
        try:
            symbol = f"{asset}/USDT"
            ticker = exchange.fetch_ticker(symbol)
            prices[asset] = float(ticker['last'])
            continue
        except:
            pass
        prices[asset] = 0.0
    return prices

def load_json(filepath):
    try:
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return {}

def load_logs(filepath, lines=100):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(deque(f, maxlen=lines))
    except:
        return []

def load_logs_by_hours(filepath, hours, max_lines=10000):
    if not os.path.exists(filepath):
        return ""
    cutoff = datetime.now() - timedelta(hours=hours)
    selected = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if len(line) < 19:
                    continue
                ts_str = line[:19]
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if ts >= cutoff:
                    selected.append(line)
        if not selected:
            return ""
        if len(selected) > max_lines:
            selected = selected[-max_lines:]
        return "".join(selected)
    except Exception:
        return ""

# Header
ensure_state_file(STATE_FILE)
state = load_json(STATE_FILE)
learning_data = load_json(LEARNING_FILE)

# Emergency Stop Check
if os.path.exists("data/emergency_stop.flag"):
    st.error("🚨 ACİL DURDURMA AKTİF! Bot durduruldu. Dosya dizininden 'data/emergency_stop.flag' dosyasını silmeden bot tekrar çalışmaz.")
    if st.button("✅ Acil Durumu Kaldır (Reset)"):
        try:
            os.remove("data/emergency_stop.flag")
            st.rerun()
        except Exception as e:
            st.error(f"Dosya silinemedi: {e}")

is_live = False
if state:
    is_live = state.get('is_live', False)

# Debug Info in Sidebar
with st.sidebar.expander("🔍 Debug Info", expanded=False):
    st.write(f"**Last Load:** {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"STATE_FILE: {STATE_FILE}")
    try:
        exists = os.path.exists(STATE_FILE)
    except Exception:
        exists = False
    st.caption(f"STATE_FILE exists: {exists}")
    if state:
        st.write(f"**State Keys:** {list(state.keys())}")
        com = state.get('commentary', {})
        wallet_debug = state.get('wallet_assets', {})
        if com:
            st.write(f"**Commentary Keys:** {list(com.keys())}")
        else:
            st.error("Commentary is empty or missing!")
        if wallet_debug:
            st.caption("Wallet Assets (Raw)")
            st.json(wallet_debug)
    else:
        st.warning("State yüklenemedi veya henüz oluşturulmadı.")

mode_title = "CANLI İŞLEM (LIVE TRADING)" if is_live else "Paper Trading (Simülasyon)"
icon = "🔥" if is_live else "🧪"

st.title(f"{icon} Kripto Bot Dashboard | {mode_title}")
st.markdown("---")

# Auto-refresh mechanism
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

# Refresh button & Auto-refresh toggle
col_refresh, col_auto, col_status, col_danger = st.columns([1, 2, 3, 2])
with col_refresh:
    if st.button('🔄 Yenile'):
        st.rerun()

with col_auto:
    auto_refresh = st.checkbox('Otomatik Yenile (5sn)', value=st.session_state.auto_refresh)
    if auto_refresh:
        st.session_state.auto_refresh = True
        time.sleep(5)
        st.rerun()
    else:
        st.session_state.auto_refresh = False

with col_danger:
    if st.button('🚨 ACİL DURDUR', type="primary"):
        with open("data/emergency_stop.flag", "w") as f:
            f.write("STOP")
        st.rerun()

if not state:
    st.warning("⚠️ Bot verisi henüz oluşmadı. Botun çalışır durumda olduğundan emin olun.")
else:
    # Show data age
    last_updated_ts = state.get('last_updated', 0)
    if last_updated_ts > 0:
        dt_object = datetime.fromtimestamp(last_updated_ts)
        time_str = dt_object.strftime("%H:%M:%S")
        st.caption(f"Veri Güncelleme Saati: {time_str} ({(time.time() - last_updated_ts):.1f} sn önce)")

    # 1. Key Metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    stats = state.get('stats', {})
    positions = state.get('paper_positions', {})
    wallet = state.get('wallet_assets', {})
    total_try = state.get('total_balance', 0.0)

    # Default to state stats
    total_trades = stats.get('trades', 0)
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    total_pnl = stats.get('total_pnl_pct', 0.0)
    
    # Open positions count
    open_positions_count = len(positions) if positions else 0

    # --- Pre-calculate Total Asset Value for Metric ---
    total_asset_value_usdt = 0.0
    if wallet:
        try:
            w_df_temp = pd.DataFrame.from_dict(wallet, orient='index')
            w_df_temp['Varlık'] = w_df_temp.index
            w_df_temp = w_df_temp[w_df_temp['total'] > 0]
            
            assets_list = w_df_temp['Varlık'].tolist()
            price_map = get_asset_prices_in_usdt(assets_list)
            
            for index, row in w_df_temp.iterrows():
                asset = row['Varlık']
                amount = row['total']
                price = price_map.get(asset, 0.0)
                total_asset_value_usdt += amount * price
        except Exception as e:
            pass # Fail silently for metric, handled in table
    
    # If calculated value > 0 and LIVE, use it. 
    # If PAPER mode, prefer the executor calculated total_balance which includes paper positions + paper cash
    if is_live and total_asset_value_usdt > 0:
        display_balance = total_asset_value_usdt
        balance_label = "Toplam Bakiye (Canlı)"
        balance_help = "Cüzdandaki gerçek varlıkların USDT karşılığı"
    elif not is_live:
        display_balance = total_try # This is set by executor to be paper_balance + paper_pos_value
        balance_label = "Toplam Bakiye (Paper)"
        balance_help = "Sanal Nakit + Açık Pozisyon Değerleri"
    else:
        display_balance = total_try 
        balance_label = "Toplam Bakiye"
        balance_help = "Hesaplanan bakiye"

    # Override with learning_data if available (more persistent)
    if learning_data:
        g_stats = learning_data.get('global_stats', {})
        history = learning_data.get('trade_history', [])
        
        if g_stats or history:
            total_trades = g_stats.get('total_trades', len(history))
            wins = g_stats.get('wins', 0)
            losses = total_trades - wins
            
            # Recalculate total PnL from history if needed
            if history:
                total_pnl = sum(t.get('pnl', 0.0) for t in history)

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    avg_pnl = (total_pnl / total_trades) if total_trades > 0 else 0
    
    col1.metric(balance_label, f"{display_balance:.2f} USDT", help=balance_help)
    
    if not is_live:
        paper_bal = state.get('paper_balance', 0.0)
        col1.caption(f"Sanal Nakit: {paper_bal:.2f} USDT")
        col1.info("🧪 SİMÜLASYON MODU")

    col2.metric("Açık Pozisyonlar", f"{open_positions_count} Adet")
    col3.metric("Tamamlanan İşlem", f"{total_trades}")
    col4.metric("Kazanma Oranı", f"%{win_rate:.1f}")
    col5.metric("Ortalama PnL", f"%{avg_pnl:.2f}", delta=f"{avg_pnl:.2f}%")
    
    with st.expander("🧠 Parametre Danışmanı ve Meta Skor Önerileri", expanded=False):
        if not learning_data:
            st.info("Henüz öğrenme verisi yok.")
        else:
            advisor = learning_data.get("param_advisor", {})
            last_result = advisor.get("last_result", {})
            suggestions = last_result.get("suggestions", [])
            if not last_result or not suggestions:
                st.info("Henüz kaydedilmiş parametre önerisi yok.")
            else:
                ts = last_result.get("timestamp", 0)
                if ts:
                    dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    st.caption(f"Son Çalışma: {dt_str}")
                regime_info = last_result.get("regime", {})
                if regime_info:
                    st.write(f"Piyasa Rejimi: {regime_info.get('status', 'Bilinmiyor')} | WinRate 24h: %{regime_info.get('win_rate_24h', 0):.1f}")
                type_counts = {}
                for s in suggestions:
                    t = s.get("type", "unknown")
                    type_counts[t] = type_counts.get(t, 0) + 1
                if type_counts:
                    st.write("Öneri Tipleri:")
                    for t, c in type_counts.items():
                        st.write(f"- {t}: {c} adet")
                meta_sugs = [s for s in suggestions if s.get("type") == "meta_score"]
                if meta_sugs:
                    m = meta_sugs[0]
                    conf = m.get("suggested", {})
                    trsi = conf.get("target_rsi")
                    tvol = conf.get("target_volume_ratio")
                    if trsi is not None and tvol is not None:
                        st.write(f"CUSTOM_EDGE_SCORE hedefleri: RSI ≈ {float(trsi):.1f}, Volume Ratio ≈ {float(tvol):.2f}")
                tune_sugs = [s for s in suggestions if s.get("type") == "tune"]
                if tune_sugs:
                    df_tune = []
                    for s in tune_sugs:
                        df_tune.append({
                            "Parametre": s.get("target"),
                            "Mevcut": s.get("current"),
                            "Önerilen": s.get("suggested"),
                            "Açıklama": s.get("reason", "")
                        })
                    st.dataframe(pd.DataFrame(df_tune), hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    # --- NEW SECTION: Bot Commentary ---
    commentary = state.get('commentary', {})
    
    # Brain Plan History count
    history = commentary.get('brain_plan_history', [])
    history_count = len(history)
    
    if commentary:
        st.subheader("🤖 Bot'un Analiz ve Yorumları")
        
        # 1. Market & Strategy
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"**Aktif Strateji:** {commentary.get('active_strategy', 'Bilinmiyor')}")
        with c2:
            regime = commentary.get('market_regime', {})
            if regime:
                trend = regime.get('trend', 'SIDEWAYS')
                if trend == 'ANALYZING':
                    trend = 'SIDEWAYS'
                vol = regime.get('volatility', 'LOW')
                st.write(f"**Piyasa Durumu:** Trend: `{trend}` | Volatilite: `{vol}`")
            else:
                st.write("**Piyasa Durumu:** Veri yok")

        # 2. Portfolio & Opportunities
        # Update Tab Titles with Counts
        tab1_title = "💼 Portföy Analizi"
        tab2_title = "✨ Fırsatlar"
        tab3_title = f"🧠 Brain Planı ({history_count})"
        
        tab1, tab2, tab3 = st.tabs([tab1_title, tab2_title, tab3_title])
        
        with tab1:
            p_comments = commentary.get('portfolio_analysis', {})
            if p_comments:
                for sym, data in p_comments.items():
                    color = "green" if data['pnl_pct'] > 0 else "red"
                    st.markdown(f"**{sym}**: :{color}[{data['comment']}]")
            else:
                st.info("Portföyde yorumlanacak aktif pozisyon yok.")

        with tab2:
            top_opps = commentary.get('top_opportunities', [])
            if top_opps:
                for opp in top_opps:
                    st.success(f"**{opp['symbol']}** - Skor: **{opp['score']:.2f}**\n\nFiyat: {opp['price']} | {opp['reason']}")
            else:
                st.info("Şu an öne çıkan yüksek skorlu fırsat yok.")

        with tab3:
            st.info("Brain'in aldığı kararların ve planlamaların tarihçesi.")
            
            if history:
                # Reverse to show newest first
                for log_entry in reversed(history):
                    ts = log_entry.get('timestamp', 0)
                    dt_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                    action = log_entry.get('action', 'INFO')
                    reason = log_entry.get('reason', '')
                    
                    icon = "ℹ️"
                    if action == "SWAP_READY": icon = "🔄"
                    elif action == "HOLD": icon = "🛡️"
                    elif action == "WAIT": icon = "⏳"
                    elif action == "BUY": icon = "🟢"
                    elif action == "SELL": icon = "🔴"
                    
                    with st.expander(f"{icon} {dt_str} - {action}"):
                        st.write(f"**Gerekçe:** {reason}")
                        details = log_entry.get('details', {})
                        if details:
                            st.json(details)
            else:
                st.warning("Henüz kaydedilmiş bir plan verisi yok. Botun çalışmasını bekleyin.")
        
        st.markdown("---")
    else:
        st.info("⏳ Bot şu an piyasa verilerini topluyor ve analiz yapıyor. Lütfen ilk taramanın bitmesini bekleyin...")
    
    # 2. Wallet Balances
    if wallet:
        st.subheader("💰 Cüzdan Varlıkları (Binance Global)")
        
        # Calculate Total Asset Value in USDT
        total_asset_value_usdt = 0.0
        exchange = get_exchange()
        
        w_df = pd.DataFrame.from_dict(wallet, orient='index')
        w_df['Varlık'] = w_df.index
        w_df = w_df[['Varlık', 'free', 'locked', 'total']]
        w_df.columns = ['Varlık', 'Kullanılabilir', 'Kilitli', 'Toplam']
        
        # Filter small dust
        w_df = w_df[w_df['Toplam'] > 0]
        
        # --- OPTIMIZED PRICE FETCHING ---
        # Get unique assets list
        assets_list = w_df['Varlık'].tolist()
        
        # Fetch prices (Cached)
        try:
            price_map = get_asset_prices_in_usdt(assets_list)
        except Exception as e:
            st.error(f"Fiyatlar çekilemedi: {e}")
            price_map = {a: 0.0 for a in assets_list}

        # Calculate values
        asset_values_display = []
        
        for index, row in w_df.iterrows():
            asset = row['Varlık']
            amount = row['Toplam']
            
            # Get price from map
            price = price_map.get(asset, 0.0)
            val = amount * price
            
            if val > 0:
                total_asset_value_usdt += val
                asset_values_display.append(f"${val:,.2f}")
            else:
                asset_values_display.append("-")
                
        w_df['Tahmini Değer (USDT)'] = asset_values_display
        
        st.metric("💎 Toplam Varlık Değeri (Cüzdan)", f"${total_asset_value_usdt:,.2f}", help="Cüzdanınızdaki tüm varlıkların (USDT + Kripto) güncel kurdan hesaplanan toplam değeri.")
        
        st.dataframe(w_df, hide_index=True)
        st.subheader("🔎 Ham Cüzdan Verisi (API Snapshot)")
        st.json(wallet)
        st.markdown("---")

    # 3. Active Positions Table
    st.subheader(f"📋 Bot Tarafından Açılan Pozisyonlar ({len(positions)})")
    
    if positions:
        pos_data = []
        exchange = get_exchange()
        
        # Collect symbols to fetch prices (optional: batch fetch if needed, but loop is fine for few positions)
        for symbol, val in positions.items():
            # Handle both float and dict formats
            entry_time_str = "-"
            duration_str = "-"
            
            if isinstance(val, dict):
                # Try multiple keys for price
                entry_price = val.get('entry_price', val.get('price', 0.0))
                
                ts = val.get('timestamp', 0)
                if ts > 0:
                     dt = datetime.fromtimestamp(ts)
                     entry_time_str = dt.strftime('%H:%M:%S')
                     duration = int(time.time() - ts)
                     # Format duration
                     mins, secs = divmod(duration, 60)
                     hours, mins = divmod(mins, 60)
                     if hours > 0:
                         duration_str = f"{hours}sa {mins}dk"
                     else:
                         duration_str = f"{mins}dk {secs}sn"
            else:
                entry_price = val

            current_price = 0.0
            pnl_pct = 0.0
            
            try:
                ticker = exchange.fetch_ticker(symbol)
                current_price = float(ticker['last'])
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            except:
                pass
            
            pos_data.append({
                "Symbol": symbol,
                "Entry Price ($)": f"{entry_price:.4f}",
                "Current Price ($)": f"{current_price:.4f}",
                "PnL (%)": pnl_pct, # Keep raw for styling
                "Entry Time": entry_time_str,
                "Duration": duration_str,
                "Status": "HOLD"
            })
        
        df_pos = pd.DataFrame(pos_data)
        
        # Style Dataframe (Color PnL)
        def color_pnl(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}'

        # Format columns for display
        df_display = df_pos.copy()
        df_display['PnL (%)'] = df_display['PnL (%)'].apply(lambda x: f"%{x:.2f}")
        
        st.dataframe(df_display, width=None, use_container_width=True) 
    else:
        st.info("Şu an açık pozisyon yok.")

    # 3. Stats Details
    st.markdown("---")
    st.subheader("📊 İstatistik Detayları")
    
    col_a, col_b = st.columns(2)
    
    # Calculate daily PnL from state if available
    daily_pnl = stats.get('daily_realized_pnl', 0.0)
    daily_count = stats.get('daily_trade_count', 0)
    
    with col_a:
        st.write(f"**Kazançlı İşlemler:** {wins}")
        st.write(f"**Zararlı İşlemler:** {losses}")
        
        # Daily Stats Display
        st.markdown("---")
        st.write(f"**📅 Bugün Yapılan İşlem:** {daily_count}")
        daily_color = "green" if daily_pnl >= 0 else "red"
        st.markdown(f"**📅 Günlük PnL:** <span style='color:{daily_color}'>%{daily_pnl:.2f}</span>", unsafe_allow_html=True)
        if daily_pnl <= -5.0:
            st.error("⚠️ GÜNLÜK ZARAR LİMİTİ AŞILDI! Yeni işlem yapılmayacak.")

    with col_b:
        if total_trades > 0:
            st.progress(win_rate / 100, text=f"Başarı Oranı: %{win_rate:.1f}")

    # Timestamp
    last_updated = state.get('last_updated', 0)
    if last_updated:
        dt_object = datetime.fromtimestamp(last_updated)
        st.caption(f"Son Güncelleme: {dt_object.strftime('%Y-%m-%d %H:%M:%S')}")

    # 3. Trade History
    st.markdown("---")
    history_title = "📜 İşlem ve Emir Geçmişi (Order History)"
    if not is_live:
        history_title += " | [SİMÜLASYON]"
    
    st.subheader(history_title)
    if not is_live:
         st.caption("ℹ️ Aşağıdaki işlemler Paper Trading (Sanal) modunda gerçekleşen simülasyon emirleridir. Gerçek bakiye etkilenmez.")
    
    hist_data = []
    
    # 1. Try loading Order History (New System)
    order_history = state.get('order_history', [])
    
    if order_history:
        for order in reversed(order_history):
            ts = order.get('timestamp', 0)
            time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            action = order.get('action', 'UNKNOWN')
            symbol = order.get('symbol', '')
            price = order.get('price', 0.0)
            qty = order.get('quantity', 0.0)
            pnl_pct = order.get('pnl_pct')
            
            row = {
                "Zaman": time_str,
                "Sembol": symbol,
                "İşlem": action,
                "Fiyat ($)": f"{price:.4f}",
                "Miktar": f"{qty:.4f}",
                "Durum": order.get('status', 'FILLED')
            }
            
            if pnl_pct is not None:
                row["PnL (%)"] = f"%{pnl_pct:.2f}"
            else:
                row["PnL (%)"] = "-"
                
            hist_data.append(row)
            
    # 2. Fallback to Legacy Trade History if Order History is empty
    elif learning_data and "trade_history" in learning_data:
        history = learning_data["trade_history"]
        if history:
            for trade in reversed(history): # Show newest first
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                
                # Format timestamp
                ts = trade.get('timestamp', 0)
                time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                
                hist_data.append({
                    "Zaman": time_str,
                    "Sembol": trade['symbol'],
                    "İşlem": "TRADE (Legacy)",
                    "Fiyat ($)": f"{entry_price:.4f} -> {exit_price:.4f}",
                    "Miktar": "-",
                    "Durum": "CLOSED",
                    "PnL (%)": f"%{trade['pnl']:.2f}"
                })

    if hist_data:
        df_hist = pd.DataFrame(hist_data)
        
        # Apply color styling
        def color_row(row):
            action = str(row.get('İşlem', ''))
            pnl = str(row.get('PnL (%)', ''))
            
            styles = []
            
            # Action colors
            if action == 'BUY':
                styles.append('color: green')
            elif action == 'SELL':
                if '-' in pnl and pnl != '-': # Negative PnL
                    styles.append('color: red')
                else:
                    styles.append('color: blue')
            else:
                styles.append('')
                
            return styles * len(row) # Apply to full row (simplified) or specific cells

        # Better approach: Style specific columns
        def style_df(df):
            return df.style.applymap(lambda x: 'color: green; font-weight: bold' if x == 'BUY' else ('color: red; font-weight: bold' if x == 'SELL' else ''), subset=['İşlem'])\
                           .applymap(lambda x: 'color: red' if isinstance(x, str) and '-%' in x else ('color: green' if isinstance(x, str) and '%' in x and '-%' not in x else ''), subset=['PnL (%)'])

        st.dataframe(
            style_df(df_hist),
            width=None,
            use_container_width=True,
            height=400
        )
    else:
        st.info("Geçmiş işlem veya emir bulunamadı.")

    # 4. Live Logs
    st.markdown("---")
    st.subheader("📝 Canlı Loglar")
    
    logs = load_logs(LOG_FILE)
    log_text = "".join(logs) if logs else "Henüz log kaydı yok."
    st.text_area("Bot Activity Log", log_text, height=300, disabled=True)
    
    col_log_3h, col_log_12h = st.columns(2)
    logs_3h = load_logs_by_hours(LOG_FILE, hours=3)
    logs_12h = load_logs_by_hours(LOG_FILE, hours=12)
    with col_log_3h:
        st.download_button(
            label="⬇️ Son 3 Saatlik Logu İndir",
            data=logs_3h or "Bu aralıkta log bulunamadı.",
            file_name=f"bot_log_last_3h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="download_log_3h"
        )
    with col_log_12h:
        st.download_button(
            label="⬇️ Son 12 Saatlik Logu İndir",
            data=logs_12h or "Bu aralıkta log bulunamadı.",
            file_name=f"bot_log_last_12h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="download_log_12h"
        )

# Optional auto-refresh loop
if st.session_state.get('auto_refresh', False):
    time.sleep(5)
    st.rerun()
