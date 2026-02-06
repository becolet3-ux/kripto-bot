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
from src.sentiment.analyzer import SentimentAnalyzer
from src.strategies.grid_trading import GridTrading
from src.strategies.opportunity_manager import OpportunityManager
from src.utils.logger import log

async def run_bot():
    log(f"Starting Crypto Bot (Mock Mode: {settings.USE_MOCK_DATA})")
    log(f"Live Trading: {settings.LIVE_TRADING}")
    log(f"Monitoring Symbols: {settings.SYMBOLS}")
    
    loader = BinanceDataLoader()
    funding_loader = FundingRateLoader()
    analyzer = MarketAnalyzer(funding_loader=funding_loader)
    
    sentiment_analyzer = SentimentAnalyzer(
        twitter_api_key=settings.TWITTER_API_KEY,
        reddit_credentials={
            'client_id': settings.REDDIT_CLIENT_ID,
            'client_secret': settings.REDDIT_CLIENT_SECRET,
            'user_agent': settings.REDDIT_USER_AGENT
        } if settings.REDDIT_CLIENT_ID else None
    )
    grid_trader = GridTrading()
    opportunity_manager = OpportunityManager()
    
    await loader.initialize()
    if not settings.IS_TR_BINANCE:
        await funding_loader.initialize()

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
                     await asyncio.to_thread(loader.exchange.load_markets)
                 
                 # Filter symbols: USDT pairs only
                 quote_currency = 'USDT'
                 
                 # Fetch tickers to sort by volume (get top 100 liquid pairs to avoid junk)
                 tickers = await asyncio.to_thread(loader.exchange.fetch_tickers)
                 
                 active_symbols = []
                 sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)
                 
                 for symbol, ticker in sorted_tickers:
                     if symbol.endswith(f'/{quote_currency}') and loader.exchange.markets[symbol]['active']:
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
    
    # Scores cache for swap logic
    latest_scores = {}

    try:
        # Emergency Flag Check
        if os.path.exists(settings.EMERGENCY_STOP_FILE):
             log("🚨 EMERGENCY STOP FLAG DETECTED! Stopping bot...")
             return

        while True:
            # Emergency Flag Check (In Loop)
            if os.path.exists(settings.EMERGENCY_STOP_FILE):
                 log("🚨 EMERGENCY STOP TRIGGERED! Shutting down immediately.")
                 break

            # Günlük Zarar Limiti Kontrolü (Yeni)
            if await executor.check_daily_loss_limit():
                log("🛑 Günlük zarar limiti aşıldı, bot durduruluyor.")
                break

            log("\n--- Scanning Market ---")
            
            # 0. Update Funding Rates (Phase 4)
            if not settings.IS_TR_BINANCE:
                await funding_loader.update_funding_rates()
            
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
                # Rate Limit Smoothing (Client Side) - Optimized sleep
                await asyncio.sleep(0.1) 

                # Progress indicator every 20 symbols
                if (i + 1) % 20 == 0:
                    log(f"⏳ Scanned {i + 1}/{len(settings.SYMBOLS)} symbols...")

                # Use get_ohlcv for Spot Strategy
                # Timeframe changed to 1h for better trend following
                candles = await loader.get_ohlcv(symbol, timeframe='1h', limit=50)
                
                if candles:
                    scanned_count += 1
                    current_price = float(candles[-1][4])
                    current_prices_map[symbol] = current_price
                    
                    # --- Sentiment Analysis ---
                    sentiment_score = 0.0
                    try:
                        sentiment_score = await asyncio.to_thread(sentiment_analyzer.get_sentiment, symbol)
                    except Exception as e:
                        pass

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
                    pre_signal = analyzer.analyze_spot(symbol, candles)
                    
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
                                    if regime_4h['trend'] == 'DOWN':
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
            
            if scanned_count > 0:
                log(f"✅ Scan Complete. Checked {scanned_count} symbols. Found {signals_found} signals.")
                
                # Update Ghost Trades (Paper Trail)
                if current_prices_map:
                    executor.brain.update_ghost_trades(current_prices_map)
                
                # --- Commentary Generation (Dashboard) ---
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
                            # Fallback if pos is just a number (unlikely but safe)
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
                        all_market_signals
                    )
                    
                    # Sadece durum değiştiyse veya son logdan bu yana 5 dakika geçtiyse kaydet
                    # (Log kirliliğini önlemek için)
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

                # --- Opportunity Cost Management (Swap Logic) ---
                # Eğer alım yapılmadıysa veya bakiye kısıtlıysa takas fırsatlarını kontrol et
                # Not: Bakiye kontrolünü Executor içinde yapmak daha doğru ama şimdilik sinyal bazlı bakalım
                if executor.paper_positions and all_market_signals:
                    swap_opp = opportunity_manager.check_for_swap_opportunity(
                        executor.paper_positions, 
                        all_market_signals
                    )
                    
                    if swap_opp:
                        log(f"🔄 SWAP OPPORTUNITY DETECTED: Sell {swap_opp['sell_symbol']} -> Buy {swap_opp['buy_signal'].symbol} ({swap_opp['reason']})")
                        
                        # 1. Sell the old asset
                        sell_signal = TradeSignal(
                            symbol=swap_opp['sell_symbol'],
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
                        
                # Her döngü sonunda cüzdanı güncelle
                if settings.LIVE_TRADING:
                     await executor.sync_wallet_balances()
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
