import asyncio
import sys
import os
import time
import pandas as pd
from typing import List
import urllib3

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add project root to path
sys.path.append(os.getcwd())

from config.settings import settings
from src.collectors.binance_loader import BinanceDataLoader
# from src.collectors.binance_tr_client import BinanceTRClient
from src.collectors.funding_rate_loader import FundingRateLoader
from src.strategies.analyzer import MarketAnalyzer, TradeSignal
from src.execution.executor import BinanceExecutor
from src.strategies.grid_trading import GridTrading
from src.strategies.opportunity_manager import OpportunityManager
from src.utils.logger import log

async def update_dashboard_commentary(executor, opportunity_manager, market_regime, all_market_signals, current_prices_map, latest_scores=None):
    """
    Dashboard için yorumları ve durumu günceller.
    """
    try:
        # 1. Top Opportunities
        sorted_signals = sorted([s for s in all_market_signals if s.action == 'ENTRY'], key=lambda x: x.score, reverse=True)
        top_opps = []
        for s in sorted_signals[:5]:
            top_opps.append({
                "symbol": s.symbol,
                "score": s.score,
                "price": s.details.get('close', 0),
                "reason": "Yüksek Skorlu Sinyal"
            })

        # 2. Portfolio Commentary
        portfolio_comments = {}
        for sym, pos in executor.paper_positions.items():
            # Handle new/old dict structure safely
            p_entry = 0.0
            p_qty = 0.0
            if isinstance(pos, dict):
                p_entry = pos.get('entry_price', pos.get('price', 0))
                p_qty = pos.get('quantity', 0)
            else:
                # Fallback if pos is just a number
                p_entry = float(pos)

            p_current = current_prices_map.get(sym, p_entry)
            # Avoid division by zero
            p_pnl = ((p_current - p_entry) / p_entry) * 100 if p_entry > 0 else 0.0
            
            comment = f"Maliyet: {p_entry:.4f}. "
            if p_pnl > 0:
                comment += f"Kar: %{p_pnl:.2f} 🟢"
            else:
                comment += f"Zarar: %{p_pnl:.2f} 🔴"
            
            portfolio_comments[sym] = {
                "pnl_pct": p_pnl,
                "comment": comment,
                "value": p_qty * p_current
            }

        # 3. Strategy Status
        strategy_status = "Bilinmiyor"
        if market_regime:
            if market_regime['trend'] == 'SIDEWAYS':
                strategy_status = "Yatay Piyasa (Grid Trading Aktif) 🕸️"
            else:
                strategy_status = f"Trend Piyasası ({market_regime['trend']}) - Spot Strateji Aktif 🚀"

        commentary = {
            "market_regime": market_regime,
            "active_strategy": strategy_status,
            "top_opportunities": top_opps,
            "portfolio_analysis": portfolio_comments,
            "last_updated": time.time(),
            "brain_plan": None
        }

        # --- 4. Brain Plan Log (Why/Why Not Swap) ---
        # Mevcut brain_plan geçmişini koru
        existing_commentary = executor.full_state.get('commentary', {})
        plan_history = existing_commentary.get('brain_plan_history', [])

        # Portföy boş olsa bile durum analizi yap
        plan_analysis = opportunity_manager.analyze_swap_status(
            executor.paper_positions,
            all_market_signals,
            score_cache=latest_scores
        )
        
        # Sadece durum değiştiyse veya son logdan bu yana 5 dakika geçtiyse kaydet
        should_log = True
        if plan_history:
            last_log = plan_history[-1]
            time_diff = time.time() - last_log['timestamp']
            if last_log['reason'] == plan_analysis['reason'] and time_diff < 300:
                should_log = False
        
        if should_log:
            new_log = {
                "timestamp": time.time(),
                "action": plan_analysis['action'],
                "reason": plan_analysis['reason'],
                "details": plan_analysis.get('details', {})
            }
            plan_history.append(new_log)
            # Keep last 50 entries
            if len(plan_history) > 50:
                plan_history = plan_history[-50:]
        
        commentary['brain_plan_history'] = plan_history
        
        executor.update_commentary(commentary)

    except Exception as e:
        log(f"⚠️ Failed to generate commentary: {e}")

async def run_bot():
    log(f"Starting Crypto Bot (Mock Mode: {settings.USE_MOCK_DATA})")
    log(f"Live Trading: {settings.LIVE_TRADING}")
    log(f"Monitoring Symbols: {settings.SYMBOLS}")
    
    loader = BinanceDataLoader()
    funding_loader = FundingRateLoader()
    analyzer = MarketAnalyzer(funding_loader=funding_loader)
    
    sentiment_analyzer = None
    try:
        from src.sentiment.analyzer import SentimentAnalyzer
        # Always initialize for Fear & Greed Index support
        # Keys are only passed if SENTIMENT_ENABLED is True
        sentiment_analyzer = SentimentAnalyzer(
            twitter_api_key=settings.TWITTER_API_KEY if settings.SENTIMENT_ENABLED else None,
            reddit_credentials={
                'client_id': settings.REDDIT_CLIENT_ID,
                'client_secret': settings.REDDIT_CLIENT_SECRET,
                'user_agent': settings.REDDIT_USER_AGENT
            } if settings.SENTIMENT_ENABLED and settings.REDDIT_CLIENT_ID else None
        )
    except Exception as e:
        log(f"⚠️ Sentiment Analyzer Init Failed: {e}")
        sentiment_analyzer = None
    grid_trader = GridTrading()
    opportunity_manager = OpportunityManager()
    
    # 4. Initialize Data Sources
    try:
        await asyncio.wait_for(loader.initialize(), timeout=60.0)
    except Exception as e:
        log(f"⚠️ Loader initialization timed out or failed: {e}")
        # Proceed, maybe loader switched to mock internally or we handle it later
    
    # Funding loader is updated in the loop, no need to block startup
    # if not settings.IS_TR_BINANCE:
    #     await funding_loader.initialize()

    # Initialize Executor with the exchange client from loader
    exchange_client = None
    if hasattr(loader, 'exchange'):
        exchange_client = loader.exchange
        
    executor = BinanceExecutor(exchange_client=exchange_client, is_tr=settings.IS_TR_BINANCE)


    # Dynamic Symbol Loading for Binance TR (DISABLED)
    # if settings.LIVE_TRADING and settings.IS_TR_BINANCE and not settings.USE_MOCK_DATA:
    #     log("🔄 Fetching ALL Active Pairs from Binance TR...")
    #     try:
    #          # We can access the underlying client. Since it's sync, we can run it in thread.
    #          if hasattr(loader, 'exchange') and isinstance(loader.exchange, BinanceTRClient):
    #              # Fetch up to 1000 symbols (effectively all active pairs)
    #              top_symbols = await asyncio.to_thread(loader.exchange.get_top_symbols, limit=1000)
    #              if top_symbols:
    #                  settings.SYMBOLS = top_symbols
    #                  log(f"✅ Updated Scanning List: {len(settings.SYMBOLS)} Symbols (ALL)")
    #              else:
    #                  log("⚠️ Could not fetch top symbols, using default list.")
    #     except Exception as e:
    #          log(f"⚠️ Failed to update symbols: {e}")

    # Dynamic Symbol Loading for Binance Global (Futures/Spot)
    if not settings.IS_TR_BINANCE and not settings.USE_MOCK_DATA:
        log("🔄 Fetching Active Pairs from Binance Global...")
        try:
            if hasattr(loader, 'exchange'):
                # Ensure markets are loaded
                if not loader.exchange.markets:
                    log("⏳ Loading markets...")
                    await asyncio.wait_for(asyncio.to_thread(loader.exchange.load_markets), timeout=60.0)
                
                # Test connection with single ticker first
                log("🔍 Testing connection with BTC/USDT...")
                await asyncio.wait_for(asyncio.to_thread(loader.exchange.fetch_ticker, 'BTC/USDT'), timeout=10.0)
                log("✅ Connection verified.")

                # Filter symbols: USDT pairs only
                quote_currency = 'USDT'
                
                # Fetch tickers to sort by volume (get top 100 liquid pairs to avoid junk)
                log("📊 Fetching ALL tickers for volume analysis (this may take a moment)...")
                # Increase timeout for full ticker fetch as it can be heavy (20MB+ data)
                tickers = await asyncio.wait_for(asyncio.to_thread(loader.exchange.fetch_tickers), timeout=60.0)
                log(f"DEBUG: Fetched {len(tickers)} tickers. Sample: {list(tickers.keys())[:5]}")
                
                active_symbols = []
                sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)
                
                for symbol, ticker in sorted_tickers:
                        # log(f"DEBUG: Checking {symbol} - Active: {loader.exchange.markets.get(symbol, {}).get('active')}")
                        # Handle CCXT Futures format (e.g. BTC/USDT:USDT) and Spot (BTC/USDT)
                        is_usdt_pair = '/USDT' in symbol
                        is_active = loader.exchange.markets.get(symbol, {}).get('active', False)
                        
                        # Blacklist check
                        blacklist = ['USDC', 'TUSD', 'FDUSD', 'DAI', 'USDP', 'USDe', 'EURI', 'EUR', 'AEUR', 'USD1', 'BUSD', 'RLUSD']
                        base_currency = symbol.split('/')[0]
                        if base_currency in blacklist:
                            continue

                        if is_usdt_pair and is_active:
                            active_symbols.append(symbol)
                
                if active_symbols:
                    # Limit to top 400 for broad market coverage
                    settings.SYMBOLS = active_symbols[:400]
                    log(f"✅ Updated Scanning List: {len(settings.SYMBOLS)} Symbols (Top Volume {quote_currency} Pairs)")
                else:
                    log("⚠️ No active symbols found, using default list.")
        except Exception as e:
            log(f"⚠️ Failed to update symbols: {e}")

    await executor.initialize()
    
    # Initial Dashboard Update (Empty) to prevent "Collecting Data" stuck
    await update_dashboard_commentary(
        executor, 
        opportunity_manager, 
        {"trend": "ANALYZING", "volatility": "LOW"}, 
        [], 
        {},
        latest_scores={}
    )
    
    # Scores cache for swap logic
    latest_scores = {}
    
    # Swap Confirmation Tracker (Debounce Logic)
    swap_confirmation_tracker = {}

    try:
        # Emergency Flag Check
        if os.path.exists(settings.EMERGENCY_STOP_FILE):
             log("🚨 EMERGENCY STOP FLAG DETECTED! Stopping bot...")
             return

        loop_count = 0
        while True:
            loop_count += 1
            # Emergency Flag Check (In Loop)
            if os.path.exists(settings.EMERGENCY_STOP_FILE):
                 log("🚨 EMERGENCY STOP TRIGGERED! Shutting down immediately.")
                 break

            # Günlük Zarar Limiti Kontrolü (Yeni)
            if await executor.check_daily_loss_limit():
                log("🛑 Günlük zarar limiti aşıldı, bot durduruluyor.")
                break

            log("\n--- Scanning Market ---")
            
            # Sync Wallet First!
            await executor.sync_wallet()

            # Ensure held positions are always scanned (Zombie Position Fix)
            try:
                held_symbols = list(executor.paper_positions.keys())
                for sym in held_symbols:
                    # Check if symbol is valid (has /USDT) and not already in list
                    if sym not in settings.SYMBOLS and '/USDT' in sym:
                         settings.SYMBOLS.append(sym)
                         log(f"🧟 Zombie Position Detected: {sym} added to scan list.")
            except Exception as e:
                log(f"⚠️ Failed to update scan list for held positions: {e}")

            # Periodic Dust Cleanup (Every 20 loops ~ 10-20 mins)
            if loop_count % 20 == 0:
                 if not settings.IS_TR_BINANCE:
                     await executor.convert_dust_to_bnb()
            
            # 0. Update Funding Rates (Phase 4)
            if not settings.IS_TR_BINANCE:
                await funding_loader.update_funding_rates()
            
            # 0.5 Fear & Greed Index (Global Sentiment)
            if sentiment_analyzer and loop_count % 20 == 1:
                try:
                    fng_data = await asyncio.to_thread(sentiment_analyzer.get_fear_and_greed_index)
                    if fng_data:
                         log(f"😨 Fear & Greed Index: {fng_data['value']} ({fng_data['value_classification']})")
                except Exception as e:
                    log(f"⚠️ F&G Fetch Error: {e}")

            
            # 1. Market Regime Analysis (Global Trend)
            market_regime = None
            weights = executor.brain.get_weights()
            indicator_weights = executor.brain.get_indicator_weights()
            try:
                btc_symbol = "BTC_TRY" if settings.IS_TR_BINANCE else "BTC/USDT"
                # Use longer timeframe for regime? 1h is fine for now, maybe 4h better?
                # Using 1h to match main loop speed
                btc_candles = await loader.get_ohlcv(btc_symbol, timeframe='1h', limit=50)
                if btc_candles:
                    market_regime = analyzer.analyze_market_regime(btc_candles)
                    log(f"🌍 Market Regime ({btc_symbol}): Trend={market_regime['trend']}, Volatility={market_regime['volatility']}")
            except Exception as e:
                log(f"⚠️ Failed to detect market regime: {e}")

            scanned_count = 0
            signals_found = 0
            
            # Opportunity Manager için sinyalleri topla
            all_market_signals = []
            current_prices_map = {} # For updating ghost trades
            
            log(f"🔍 Scanning {len(settings.SYMBOLS)} symbols...")

            for i, symbol in enumerate(settings.SYMBOLS):
                try:
                    # Rate Limit Smoothing (Client Side) - Optimized sleep
                    await asyncio.sleep(0.1) 

                    # Progress indicator every 20 symbols
                    if (i + 1) % 20 == 0:
                        log(f"⏳ Scanned {i + 1}/{len(settings.SYMBOLS)} symbols...")
                    
                    # Update Dashboard Commentary periodically (Every 50 symbols)
                    if (i + 1) % 50 == 0:
                        await update_dashboard_commentary(
                            executor, 
                            opportunity_manager, 
                            market_regime, 
                            all_market_signals, 
                            current_prices_map,
                            latest_scores
                        )

                    # Use get_ohlcv for Spot Strategy
                    # Timeframe changed to 1h for better trend following
                    candles = await loader.get_ohlcv(symbol, timeframe='1h', limit=50)
                    
                    if candles:
                        scanned_count += 1
                        current_price = float(candles[-1][4])
                        current_prices_map[symbol] = current_price
                        
                        # --- Sentiment Analysis ---
                        sentiment_score = 0.0
                        if settings.SENTIMENT_ENABLED and not settings.DISABLE_SENTIMENT_ANALYSIS and sentiment_analyzer:
                            try:
                                sentiment_score = 0.0
                            except Exception:
                                sentiment_score = 0.0

                        # --- Grid Trading Check ---
                        if market_regime and market_regime['trend'] == 'SIDEWAYS':
                            current_price = float(candles[-1][4])
                            
                            if symbol not in grid_trader.active_grids:
                                # 1. Bakiye ve Precision Bilgilerini Al
                                try:
                                    free_balance = await executor.get_free_balance('TRY')
                                except Exception:
                                    free_balance = 0.0

                                step_size = 1.0
                                min_qty = 0.0
                                try:
                                    info = await executor.get_symbol_info(symbol)
                                    if info:
                                        step_size = float(info.get('stepSize', '1.0'))
                                        min_qty = float(info.get('minQty', '0.0'))
                                except Exception:
                                    pass

                                # 2. Sermaye Tahsisi (Bakiyenin %90'ı, max 1000 TRY)
                                # Minimum işlem limiti genellikle 10-20 TRY'dir. Seviye başına 20 TRY ayıralım.
                                allocation = min(free_balance * 0.90, 1000.0)
                                min_required = 20.0 * grid_trader.grid_levels 
                                
                                if allocation >= min_required:
                                    grid_trader.setup_grid(
                                        symbol, 
                                        current_price, 
                                        total_capital=allocation,
                                        step_size=step_size,
                                        min_qty=min_qty
                                    )
                                    await grid_trader.place_grid_orders(symbol, executor)
                                    log(f"🕸️ Grid Started for {symbol} (Cap: {allocation:.2f} TRY)")
                                else:
                                    # Yetersiz bakiye, log kirletmemek için sessiz geçiyoruz.
                                    # Ancak debug modunda veya çok düşük bakiye varsa uyarabiliriz.
                                    pass

                            else:
                                await grid_trader.check_grid_status(symbol, current_price, executor)

                        # 0. Safety Check (Brain)
                        pre_signal = analyzer.analyze_spot(symbol, candles, exchange=loader.exchange)
                        
                        if pre_signal:
                            volatility = pre_signal.details.get('volatility', 0)
                            vol_ratio = pre_signal.details.get('volume_ratio', 1.0)
                            current_rsi = pre_signal.details.get('rsi', 50.0)
                            
                            # Step 2: Ask Brain for Permission & Advice
                            safety = executor.brain.check_safety(
                                symbol, 
                                current_volatility=volatility, 
                                volume_ratio=vol_ratio,
                                current_rsi=current_rsi
                            )
                            is_blocked = not safety['safe']
                            modifier = safety.get('modifier', 0)
                            
                            # Only log brain block if verbose or specific condition (reduced noise)
                            if is_blocked and pre_signal.action == "ENTRY":
                                 # log(f"🧠 Brain Blocked {symbol}: {safety['reason']}")
                                 executor.brain.record_ghost_trade(
                                     symbol, 
                                     current_price, 
                                     f"Brain Filter: {safety['reason']}", 
                                     pre_signal.score
                                 )

                        # Step 3: Final Analysis with Brain's Advice
                        signal = analyzer.analyze_spot(
                            symbol, 
                            candles, 
                            rsi_modifier=modifier, 
                            is_blocked=is_blocked,
                            weights=weights,
                            indicator_weights=indicator_weights,
                            market_regime=market_regime,
                            sentiment_score=sentiment_score
                        )
                        
                        # Sinyali listeye ekle (SWAP analizi için)
                        if signal:
                             all_market_signals.append(signal)
                             latest_scores[symbol] = signal.score
                        
                        # Step 3.5: Multi-timeframe Confirmation (4h) for ENTRIES
                        if signal and signal.action == "ENTRY":
                            try:
                                # Fetch 4h candles only if we have a potential entry
                                candles_4h = await loader.get_ohlcv(symbol, timeframe='4h', limit=30)
                                if candles_4h:
                                    regime_4h = analyzer.analyze_market_regime(candles_4h)
                                    # Filter: Don't buy if 4h Trend is DOWN (Major downtrend)
                                    # UNLESS it is a High Score Override
                                    if regime_4h['trend'] == 'DOWN':
                                        if hasattr(signal, 'primary_strategy') and signal.primary_strategy == "high_score_override":
                                            log(f"🚀 {symbol}: 4h Trend is DOWN but High Score Override applies. Allowing ENTRY.")
                                        else:
                                            log(f"📉 Filtered {symbol}: 1h Buy Signal but 4h Trend is DOWN.")
                                            executor.brain.record_ghost_trade(
                                                symbol, 
                                                current_price, 
                                                "Multi-TF Filter: 4h Trend DOWN", 
                                                signal.score
                                            )
                                            signal = None
                                    else:
                                        log(f"✅ Multi-TF Confirmed {symbol}: 4h Trend is {regime_4h['trend']}")
                            except Exception as e:
                                log(f"⚠️ Multi-TF Check Failed for {symbol}: {e}")
                                
                        # Step 3.6: Correlation Check (Portfolio Diversification)
                        if signal and signal.action == "ENTRY":
                            is_correlated = False
                            # Check against existing positions
                            for held_symbol in executor.paper_positions:
                                if held_symbol == symbol: continue
                                
                                try:
                                    # Use cache to get held symbol data fast
                                    # We need to await because get_ohlcv is async
                                    held_candles = await loader.get_ohlcv(held_symbol, timeframe='1h', limit=50)
                                    if held_candles:
                                        corr = analyzer.calculate_correlation(candles, held_candles)
                                        if corr > 0.85: # High correlation threshold (0.85 is strong)
                                            log(f"🔗 Correlation Alert: {symbol} is highly correlated with held {held_symbol} ({corr:.2f}). Skipping to diversify.")
                                            executor.brain.record_ghost_trade(
                                                symbol, 
                                                current_price, 
                                                f"Correlation Filter: >0.85 with {held_symbol}", 
                                                signal.score
                                            )
                                            is_correlated = True
                                            break
                                except Exception as e:
                                    log(f"⚠️ Correlation check failed for {held_symbol}: {e}")
                            
                            if is_correlated:
                                signal = None

                    else:
                        signal = None
                    
                    # 2. Risk Management Override (Phase 1: StopLossManager Integration)
                    if symbol in executor.paper_positions:
                        # Prepare data for ATR calculation
                        df_candles = None
                        if candles:
                             try:
                                 df_candles = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                                 for c in ['open', 'high', 'low', 'close', 'volume']:
                                     df_candles[c] = df_candles[c].astype(float)
                             except Exception as e:
                                 log(f"⚠️ Risk Data Prep Error ({symbol}): {e}")
                        
                        # Check Risk Conditions via Executor -> StopLossManager
                        risk_check = executor.check_risk_conditions(symbol, current_price, df_candles)
                        action = risk_check.get('action')
                        
                        if action in ['CLOSE', 'PARTIAL_CLOSE']:
                            reason = risk_check.get('reason', 'RISK_EXIT')
                            log(f"🛡️ Risk Exit Triggered [{symbol}]: {action} - {reason}")
                            
                            signal_action = "EXIT" if action == 'CLOSE' else "PARTIAL_EXIT"
                            score = -100.0 if action == 'CLOSE' else 100.0 # Partial profit is positive
                            
                            signal = TradeSignal(
                                symbol=symbol,
                                action=signal_action,
                                direction="LONG",
                                score=score,
                                estimated_yield=0.0, # Will be calculated by executor
                                timestamp=int(time.time() * 1000),
                                details={
                                    "reason": reason, 
                                    "close": current_price,
                                    "qty_pct": risk_check.get('qty_pct', 1.0)
                                }
                            )

                    # 3. Execution
                    if signal:
                        signals_found += 1
                        log(f"⚡ Signal Detected for {symbol}: {signal.action} (Score: {signal.score:.2f})")
                        await executor.execute_strategy(signal, latest_scores=latest_scores)

                except Exception as e:
                    log(f"⚠️ Error scanning {symbol}: {e}")
                    continue
            
            if scanned_count > 0:
                log(f"✅ Scan Complete. Checked {scanned_count} symbols. Found {signals_found} signals.")
                
                # Update Ghost Trades (Paper Trail)
                if current_prices_map:
                    executor.brain.update_ghost_trades(current_prices_map)
                
                # --- Commentary Generation (Dashboard) ---
                await update_dashboard_commentary(
                    executor, 
                    opportunity_manager, 
                    market_regime, 
                    all_market_signals, 
                    current_prices_map
                )
                
                # --- LOW BALANCE RECOVERY MODE (< $50) ---
                # Kullanıcı isteği: Toplam varlık < $50 ise tek varlığa düş ve en iyisini al
                total_equity = await executor.get_total_balance()
                log(f"DEBUG: Total Equity Check: ${total_equity:.2f} (Positions: {len(executor.paper_positions)})")
                LOW_BALANCE_THRESHOLD = 100.0 # Increased to 100 to ensure trigger
                
                if total_equity < LOW_BALANCE_THRESHOLD and settings.LIVE_TRADING:
                    log(f"⚠️ Düşük Bakiye Modu Aktif (${total_equity:.2f} < ${LOW_BALANCE_THRESHOLD}). Sniper Modu Devrede!")
                    
                    # 1. En iyi sinyali bul (ENTRY olanlardan) - Yüksek Kalite Filtresi (>0.75)
                    # Sniper Modu (All-In) için sadece çok güçlü sinyallere giriyoruz.
                    high_quality_signals = sorted([
                        s for s in all_market_signals 
                        if s.action == 'ENTRY' and s.score >= 0.75
                    ], key=lambda x: x.score, reverse=True)
                    
                    if not high_quality_signals:
                        if [s for s in all_market_signals if s.action == 'ENTRY']:
                             log("⏳ Sniper Modu: Giriş sinyalleri var ama yeterince güçlü değil (<0.75). Nakitte bekleniyor...")
                        best_signal = None
                    else:
                        best_signal = high_quality_signals[0]
                        
                        # --- FUTURES SENTIMENT CHECK (New Feature) ---
                        # Eğer SentimentAnalyzer aktifse, Futures L/S oranına bak
                        if sentiment_analyzer:
                            try:
                                log(f"🔍 Futures Sentiment Analizi: {best_signal.symbol}...")
                                futures_data = await sentiment_analyzer.get_futures_sentiment(best_signal.symbol)
                                ls_ratio = futures_data.get('long_short_ratio', 0)
                                if ls_ratio > 0:
                                    log(f"📊 {best_signal.symbol} Futures L/S Ratio: {ls_ratio:.2f}")
                                    
                                    # Aşırı Kalabalık Long Uyarısı
                                    if ls_ratio > 2.5:
                                        log(f"⚠️ DİKKAT: {best_signal.symbol} üzerinde aşırı Long yığılması var (Ratio: {ls_ratio}). Düzeltme riski!")
                                        # Skoru biraz düşürebiliriz veya sadece loglarız.
                                        # best_signal.score -= 1.0 
                            except Exception as e:
                                log(f"⚠️ Futures Check Failed: {e}")
                    
                    # 2. Mevcut Pozisyonları Yönet (Tek bir en iyiye düşür)
                    current_positions = list(executor.paper_positions.keys())
                    
                    for symbol in current_positions:
                        should_sell = False
                        
                        # Durum A: En iyi sinyal var ama elimizdeki o değil -> Sat (Swap için yer aç)
                        if best_signal and symbol != best_signal.symbol:
                            # User Request: Check for 5 point score difference
                            current_pos_signal = next((s for s in all_market_signals if s.symbol == symbol), None)
                            
                            # Use cache if signal missing (prevent Score 0 glitch)
                            if current_pos_signal:
                                current_score = current_pos_signal.score
                            else:
                                current_score = latest_scores.get(symbol, 0.0)

                            score_diff = best_signal.score - current_score
                            
                            if score_diff >= 5.0:
                                # Debounce Logic: 3 döngü teyit (User Request)
                                current_count = swap_confirmation_tracker.get(symbol, 0) + 1
                                swap_confirmation_tracker[symbol] = current_count
                                
                                if current_count >= 3:
                                    should_sell = True
                                    log(f"📉 Sniper Modu: {symbol} satılıyor. (Fark: {score_diff:.1f} >= 5.0 | Onay: {current_count}/3 | Yeni: {best_signal.symbol})")
                                    swap_confirmation_tracker[symbol] = 0 # Reset
                                else:
                                    log(f"⏳ Sniper Modu: {symbol} için swap şartı sağlandı ({current_count}/3). Fark: {score_diff:.1f}. Onay bekleniyor...")
                            else:
                                # Reset counter if condition is lost
                                if swap_confirmation_tracker.get(symbol, 0) > 0:
                                     log(f"✋ Sniper Modu: {symbol} swap onayı sıfırlandı. Fark düştü ({score_diff:.1f}).")
                                swap_confirmation_tracker[symbol] = 0
                                log(f"✋ Sniper Modu: {symbol} tutuluyor. Fark yetersiz ({score_diff:.1f} < 5.0).")
                        
                        # Durum B: En iyi sinyal yok ama elimizde pozisyon var -> 
                        # Eğer çoklu pozisyon varsa ve bu en iyisi değilse sat. 
                        # Veya hiç sinyal yoksa nakite geçmek isteyebiliriz? 
                        # Şimdilik: Sadece daha iyi fırsat varsa veya çoklu pozisyon varsa satalım.
                        elif len(current_positions) > 1:
                            # Birden fazla ise, sadece en iyisini (veya rastgele birini) tutmak yerine
                            # Hepsini satıp yeniden en iyisini almak daha temiz.
                            should_sell = True
                            log(f"📉 Sniper Modu: Portföy tekilleştiriliyor. {symbol} satılıyor.")
                            
                        if should_sell:
                            # FIX: Get current price for correct valuation
                            price = current_prices_map.get(symbol, 0.0)
                            if price == 0.0:
                                # Try to fallback to position entry price or 0
                                price = executor.paper_positions.get(symbol, {}).get('entry_price', 0.0)
                            
                            # FIX: Check for Dust (< 6.0 USDT) and convert directly
                            pos_qty = executor.paper_positions.get(symbol, {}).get('quantity', 0.0)
                            value_est = pos_qty * price
                            
                            # If value is small but > 0, try dust conversion immediately
                            if 0.0 < value_est < 6.0 and not settings.IS_TR_BINANCE:
                                log(f"🧹 Sniper Modu: {symbol} (Değer: ${value_est:.2f}) Dust Convert'e yönlendiriliyor.")
                                await executor.convert_dust_to_bnb()
                                # Wait for sync
                                await asyncio.sleep(1.0)
                                continue

                            # Satış Sinyali Oluştur
                            sell_signal = TradeSignal(
                                symbol=symbol,
                                action="EXIT",
                                direction="LONG",
                                score=-10.0, # Acil Satış
                                estimated_yield=0.0,
                                timestamp=int(time.time() * 1000),
                                details={
                                    "reason": "SNIPER_MODE_LIQUIDATION",
                                    "close": price  # Pass price to avoid 0.0 in executor
                                }
                            )
                            await executor.execute_strategy(sell_signal)
                            # Bakiye güncellemesi için kısa bekleme
                            await asyncio.sleep(1.0)

                    # 2.5. Dust Temizliği (BNB Convert) ve Likidasyon
                    # Satılamayan (Min limit altı) bakiyeleri BNB'ye çevir
                    if not settings.IS_TR_BINANCE:
                         log("🧹 Sniper Modu: Dust Temizliği Başlatılıyor...")
                         await executor.convert_dust_to_bnb()
                         # Cüzdanı tekrar senkronize et ki yeni BNB/USDT bakiyesi görünsün
                         await executor.sync_wallet()
                         
                         # CRITICAL: Dust convert sonrası biriken BNB'yi satmayı dene (Eğer hedef BNB değilse)
                         # Bu adım, 3.70$ BNB + 1.50$ Dust -> 5.20$ BNB -> USDT dönüşümünü sağlar.
                         if best_signal and not best_signal.symbol.startswith('BNB'):
                             # BNB/USDT var mı kontrol et
                             if 'BNB/USDT' in executor.paper_positions:
                                 log("🧹 Sniper Modu: Biriken BNB bakiyesi USDT'ye çevriliyor...")
                                 bnb_sell_signal = TradeSignal(
                                     symbol='BNB/USDT',
                                     action="EXIT",
                                     direction="LONG",
                                     score=-10.0,
                                     estimated_yield=0.0,
                                     timestamp=int(time.time() * 1000),
                                     details={"reason": "SNIPER_MODE_BNB_LIQUIDATION"}
                                 )
                                 await executor.execute_strategy(bnb_sell_signal)
                                 await asyncio.sleep(1.0)
                                 await executor.sync_wallet_balances()
                         
                    # 3. Alım Yap (Tek Atış)
                    # Eğer elimiz boşaldıysa (veya sadece hedef varlık kaldıysa) ve en iyi sinyal varsa -> FULL GİR
                    # Not: Dust convert sonrası elimizde BNB olabilir. Eğer hedef BNB değilse ve BNB satılabiliyorsa satılmalıydı.
                    # Ama BNB dust convert'ten geldiği için muhtemelen satılamaz.
                    # Bu durumda elimizdeki BNB'yi "boş" sayıp kalan USDT ile girebiliriz.
                    
                    # paper_positions'da sadece hedef varlık varsa veya hiç yoksa
                    can_buy = False
                    if len(executor.paper_positions) == 0:
                        can_buy = True
                    elif len(executor.paper_positions) == 1 and best_signal and best_signal.symbol in executor.paper_positions:
                        # Zaten hedef varlıktayız, belki ekleme yapabiliriz? 
                        # Ama Sniper modu "Tek Coin" diyor. Zaten ondaysak işlem yapmaya gerek yok.
                        can_buy = False 
                        log(f"🎯 Zaten hedef varlıktayız: {best_signal.symbol}")
                    else:
                        # Belki elimizde sadece BNB kaldı (Convert sonrası)
                        # Eğer hedef BNB değilse, BNB harici USDT ile girebiliriz.
                        # Executor bakiyeyi kontrol edip alacak.
                        can_buy = True

                    if can_buy and best_signal:
                        log(f"🎯 Sniper Modu: {best_signal.symbol} için tam bakiye ile giriş yapılıyor!")
                        
                        # Force All-In Flag
                        if best_signal.details is None: best_signal.details = {}
                        best_signal.details['force_all_in'] = True
                        
                        await executor.execute_strategy(best_signal)
                        
                        # Döngüyü burada kes (başka işlem yapma)
                        all_market_signals = [] 

                # --- Opportunity Cost Management (Swap Logic) ---
                # Eğer alım yapılmadıysa veya bakiye kısıtlıysa takas fırsatlarını kontrol et
                # Not: Bakiye kontrolünü Executor içinde yapmak daha doğru ama şimdilik sinyal bazlı bakalım
                # Sniper Modu aktifse burayı atla (zaten yukarıda hallettik)
                elif executor.paper_positions and all_market_signals:
                    swap_opp = opportunity_manager.check_for_swap_opportunity(
                        executor.paper_positions, 
                        all_market_signals
                    )
                    
                    if swap_opp:
                        # 3-Loop Confirmation Logic (Extended to Normal Mode)
                        sell_symbol = swap_opp['sell_symbol']
                        buy_symbol = swap_opp['buy_signal'].symbol
                        
                        current_count = swap_confirmation_tracker.get(sell_symbol, 0) + 1
                        swap_confirmation_tracker[sell_symbol] = current_count
                        
                        if current_count >= 3:
                            log(f"🔄 SWAP CONFIRMED: Sell {sell_symbol} -> Buy {buy_symbol} ({swap_opp['reason']} | Count: {current_count}/3)")
                            
                            # 1. Sell the old asset
                            sell_signal = TradeSignal(
                                symbol=sell_symbol,
                                action="EXIT",
                                direction="LONG",
                                score=-1.0, # Zorunlu çıkış
                                estimated_yield=0.0,
                                timestamp=int(time.time() * 1000),
                                details={"reason": "SWAP_FOR_BETTER_OPPORTUNITY"}
                            )
                            await executor.execute_strategy(sell_signal)
                            
                            # 2. Buy the new asset
                            # Biraz bekle ki bakiye güncellensin
                            await asyncio.sleep(2.0) 
                            await executor.sync_wallet_balances()
                            await executor.execute_strategy(swap_opp['buy_signal'])
                            
                            # Reset tracker
                            swap_confirmation_tracker[sell_symbol] = 0
                        else:
                            log(f"⏳ Swap Opportunity Detected: {sell_symbol} -> {buy_symbol}. Waiting for confirmation ({current_count}/3)...")
                    else:
                        # No swap opportunity found (diff < 5.0 or hold time constraint)
                        # Reset trackers for all held positions to be safe
                        if swap_confirmation_tracker:
                            # Only clear if we are in this block (meaning not in Sniper Mode)
                            # log("✋ Swap conditions not met. Resetting confirmation trackers.")
                            swap_confirmation_tracker.clear()
                        
                # Her döngü sonunda cüzdanı güncelle
                if settings.LIVE_TRADING:
                     await executor.sync_wallet_balances()
                
                # Update MTF Stats
                if hasattr(analyzer.strategy_manager, 'stats'):
                    executor.update_mtf_stats(analyzer.strategy_manager.stats)

            else:
                log("⚠️ Warning: No market data fetched. Check connection.")
                
            log(f"Sleeping for {settings.SLEEP_INTERVAL} seconds...")
            await asyncio.sleep(settings.SLEEP_INTERVAL)
            
    except KeyboardInterrupt:
        log("\nStopping bot...")
    except Exception as e:
        log(f"Critical Error: {e}")
    finally:
        await loader.close()
        await executor.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
