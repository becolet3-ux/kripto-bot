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
from src.execution.trade_manager import TradeManager
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

    # Initialize TradeManager
    trade_manager = TradeManager(
        loader=loader,
        analyzer=analyzer,
        executor=executor,
        opportunity_manager=opportunity_manager,
        grid_trader=grid_trader,
        sentiment_analyzer=sentiment_analyzer
    )


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

                # Use TradeManager to process symbol
                # Logic: Fetch Data -> Analyze -> Risk Check -> Execute if Signal
                signal = await trade_manager.process_symbol_logic(
                    symbol, 
                    market_regime, 
                    latest_scores, 
                    current_prices_map
                )
                
                if symbol in current_prices_map:
                    scanned_count += 1
                
                if signal:
                    signals_found += 1
                    all_market_signals.append(signal)
            
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
                
                # --- LOW BALANCE RECOVERY MODE (< $100) ---
                # Kullanıcı isteği: Toplam varlık < $100 ise tek varlığa düş ve en iyisini al
                total_equity = await executor.get_total_balance()
                log(f"DEBUG: Total Equity Check: ${total_equity:.2f} (Positions: {len(executor.paper_positions)})")
                LOW_BALANCE_THRESHOLD = 100.0 
                
                if total_equity < LOW_BALANCE_THRESHOLD and settings.LIVE_TRADING:
                    await trade_manager.handle_sniper_mode(all_market_signals, current_prices_map)
                
                # --- Opportunity Cost Management (Swap Logic) ---
                # Eğer alım yapılmadıysa veya bakiye kısıtlıysa takas fırsatlarını kontrol et
                # Sniper Modu aktifse burayı atla
                elif executor.paper_positions and all_market_signals:
                    await trade_manager.handle_normal_swap_logic(all_market_signals)
                        
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
