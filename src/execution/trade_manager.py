import asyncio
import time
import pandas as pd
from typing import List, Dict, Optional, Any
from src.strategies.analyzer import TradeSignal
from src.utils.logger import log
from config.settings import settings
from src.utils.exceptions import BotError, NetworkError, ExchangeError, InsufficientBalanceError

class TradeManager:
    """
    Manages the high-level trading logic, including symbol processing,
    sniper mode (low balance), and swap opportunities.
    """
    def __init__(self, loader, analyzer, executor, opportunity_manager, grid_trader, sentiment_analyzer=None):
        self.loader = loader
        self.analyzer = analyzer
        self.executor = executor
        self.opportunity_manager = opportunity_manager
        self.grid_trader = grid_trader
        self.sentiment_analyzer = sentiment_analyzer
        
        # State tracking
        self.swap_confirmation_tracker = {}

    async def process_symbol_logic(self, symbol: str, market_regime: Dict, latest_scores: Dict, current_prices_map: Dict) -> Optional[TradeSignal]:
        """
        Processes a single symbol: fetches data, runs analysis, checks safety/risk, 
        and returns a TradeSignal if one exists.
        Also handles Risk Management (StopLoss) exits immediately.
        """
        try:
            # SAFETY CHECK: Stablecoin Filter
            base_currency = symbol.split('/')[0]
            if base_currency in ['USDT', 'USDC', 'TUSD', 'FDUSD', 'DAI', 'USDP', 'BUSD', 'EUR', 'PAX', 'U', 'UST', 'USDD', 'USDK', 'USDJ', 'VAI', 'WAI', 'CUSD', 'AEUR', 'EURI', 'GUSD', 'LUSD', 'FRAX', 'SUSD', 'WBTC', 'BTCB']:
                return None

            # Rate Limit Smoothing
            await asyncio.sleep(0.1)

            # Fetch 1h candles
            candles = await self.loader.get_ohlcv(symbol, timeframe='1h', limit=50)
            
            if not candles:
                return None

            current_price = float(candles[-1][4])
            current_prices_map[symbol] = current_price
            
            # --- Sentiment Analysis ---
            sentiment_score = 0.0
            if settings.SENTIMENT_ENABLED and not settings.DISABLE_SENTIMENT_ANALYSIS and self.sentiment_analyzer:
                try:
                    sentiment_score = 0.0 # Placeholder for actual sentiment
                except Exception:
                    sentiment_score = 0.0

            # --- Grid Trading Check ---
            if market_regime and market_regime['trend'] == 'SIDEWAYS':
                await self._handle_grid_trading(symbol, current_price, market_regime)

            # --- Spot Strategy Analysis ---
            # 1. Safety Check (Brain)
            pre_signal = self.analyzer.analyze_spot(symbol, candles, exchange=self.loader.exchange)
            
            signal = None
            if pre_signal:
                signal = await self._validate_signal(pre_signal, symbol, candles, current_price, market_regime, sentiment_score)
                if signal:
                    latest_scores[symbol] = signal.score

            # --- Risk Management Override (StopLoss) ---
            risk_signal = await self._check_risk_management(symbol, candles, current_price)
            if risk_signal:
                # If risk exit is triggered, we prioritize it and execute immediately
                log(f"⚡ Risk Signal Detected for {symbol}: {risk_signal.action} (Score: {risk_signal.score:.2f})")
                await self.executor.execute_strategy(risk_signal, latest_scores=latest_scores)
                return risk_signal # Return this as the signal for this cycle

            # --- Execute Spot Signal ---
            if signal:
                log(f"⚡ Signal Detected for {symbol}: {signal.action} (Score: {signal.score:.2f})")
                await self.executor.execute_strategy(signal, latest_scores=latest_scores)
                return signal

            return None

        except InsufficientBalanceError as e:
            log(f"⚠️ Yetersiz Bakiye ({symbol}): {e}")
            
            # --- AGGRESSIVE SNIPER MODE: Force Sell to Enter New Opportunity ---
            # If we have a very high score signal but no balance, try to sell the worst performing position
            if signal and signal.score >= 25.0: # Only for excellent opportunities
                log(f"⚔️ SNIPER MODE ACTIVATED: Attempting to free up capital for {symbol} (Score: {signal.score})")
                try:
                    # 1. Get all active positions
                    positions = await self.executor.get_open_positions()
                    if positions:
                        # 2. Find the worst position (Lowest PnL or Oldest Stagnant)
                        worst_position = None
                        lowest_pnl = 9999.0
                        
                        for pos_symbol, pos_data in positions.items():
                            # Skip if it's the same symbol (shouldn't happen but safety first)
                            if pos_symbol == symbol:
                                continue
                                
                            # Calculate PnL if current price is available
                            current_price = current_prices_map.get(pos_symbol)
                            if current_price:
                                entry_price = float(pos_data.get('entry_price', 0))
                                if entry_price > 0:
                                    pnl = (current_price - entry_price) / entry_price * 100
                                    if pnl < lowest_pnl:
                                        lowest_pnl = pnl
                                        worst_position = pos_symbol
                        
                        # 3. Force Sell the worst position
                        if worst_position:
                            log(f"⚔️ SNIPER EXECUTION: Selling {worst_position} (PnL: {lowest_pnl:.2f}%) to buy {symbol}")
                            # Create a forced sell signal
                            sell_signal = TradeSignal(
                                symbol=worst_position,
                                action="EXIT",
                                direction="LONG", # Assuming Long
                                score=-99.0, # Forced exit score
                                estimated_yield=lowest_pnl,
                                timestamp=int(time.time()),
                                details={'reason': f'SNIPER_SWAP_FOR_{symbol}'}
                            )
                            # Execute Sell
                            await self.executor.execute_strategy(sell_signal, latest_scores=latest_scores)
                            
                            # --- CRITICAL FIX: Wait for Balance Update ---
                            # Binance needs time to process the sell and update USDT balance.
                            log("⏳ Waiting 5 seconds for balance update...")
                            await asyncio.sleep(5)
                            
                            # Force refresh balance
                            await self.executor.sync_wallet_balances()
                            
                            # Retry the original Buy Signal
                            log(f"⚔️ SNIPER RETRY: Re-attempting entry for {symbol}...")
                            await self.executor.execute_strategy(signal, latest_scores=latest_scores)
                            return signal
                            
                except Exception as sniper_error:
                    log(f"❌ SNIPER MODE FAILED: {sniper_error}")
            
            return None
        except ExchangeError as e:
            log(f"⚠️ Borsa Hatası ({symbol}): {e}")
            return None
        except NetworkError as e:
            log(f"⚠️ Bağlantı Hatası ({symbol}): {e}")
            return None
        except Exception as e:
            log(f"⚠️ Error processing {symbol}: {e}")
            return None

    async def _handle_grid_trading(self, symbol, current_price, market_regime):
        """Internal helper for Grid Trading logic"""
        if symbol not in self.grid_trader.active_grids:
            try:
                free_balance = await self.executor.get_free_balance('TRY')
            except Exception:
                free_balance = 0.0

            step_size = 1.0
            min_qty = 0.0
            try:
                info = await self.executor.get_symbol_info(symbol)
                if info:
                    step_size = float(info.get('stepSize', '1.0'))
                    min_qty = float(info.get('minQty', '0.0'))
            except Exception:
                pass

            # Allocation Logic
            allocation = min(free_balance * 0.90, 1000.0)
            min_required = 20.0 * self.grid_trader.grid_levels 
            
            if allocation >= min_required:
                self.grid_trader.setup_grid(
                    symbol, 
                    current_price, 
                    total_capital=allocation,
                    step_size=step_size,
                    min_qty=min_qty
                )
                await self.grid_trader.place_grid_orders(symbol, self.executor)
                log(f"🕸️ Grid Started for {symbol} (Cap: {allocation:.2f} TRY)")
        else:
            await self.grid_trader.check_grid_status(symbol, current_price, self.executor)

    async def _validate_signal(self, pre_signal, symbol, candles, current_price, market_regime, sentiment_score):
        """Validates a pre-signal with Brain, Multi-TF, and Correlation checks"""
        volatility = pre_signal.details.get('volatility', 0)
        vol_ratio = pre_signal.details.get('volume_ratio', 1.0)
        current_rsi = pre_signal.details.get('rsi', 50.0)
        
        # Brain Check
        safety = self.executor.brain.check_safety(
            symbol, 
            current_volatility=volatility, 
            volume_ratio=vol_ratio,
            current_rsi=current_rsi
        )
        is_blocked = not safety['safe']
        modifier = safety.get('modifier', 0)
        
        if is_blocked and pre_signal.action == "ENTRY":
             self.executor.brain.record_ghost_trade(
                 symbol, 
                 current_price, 
                 f"Brain Filter: {safety['reason']}", 
                 pre_signal.score
             )

        # Final Analysis
        weights = self.executor.brain.get_weights()
        indicator_weights = self.executor.brain.get_indicator_weights()
        
        signal = self.analyzer.analyze_spot(
            symbol, 
            candles, 
            rsi_modifier=modifier, 
            is_blocked=is_blocked,
            weights=weights,
            indicator_weights=indicator_weights,
            market_regime=market_regime,
            sentiment_score=sentiment_score
        )
        
        if not signal:
            return None
            
        # Multi-timeframe Confirmation (4h) for ENTRIES
        if signal.action == "ENTRY":
            try:
                candles_4h = await self.loader.get_ohlcv(symbol, timeframe='4h', limit=30)
                if candles_4h:
                    regime_4h = self.analyzer.analyze_market_regime(candles_4h)
                    if regime_4h['trend'] == 'DOWN':
                        if hasattr(signal, 'primary_strategy') and signal.primary_strategy == "high_score_override":
                            log(f"🚀 {symbol}: 4h Trend is DOWN but High Score Override applies. Allowing ENTRY.")
                        else:
                            log(f"📉 Filtered {symbol}: 1h Buy Signal but 4h Trend is DOWN.")
                            self.executor.brain.record_ghost_trade(
                                symbol, 
                                current_price, 
                                "Multi-TF Filter: 4h Trend DOWN", 
                                signal.score
                            )
                            return None
                    else:
                        log(f"✅ Multi-TF Confirmed {symbol}: 4h Trend is {regime_4h['trend']}")
            except Exception as e:
                log(f"⚠️ Multi-TF Check Failed for {symbol}: {e}")

        # Correlation Check
        if signal.action == "ENTRY":
            # --- PRO UPDATE: Bypass Correlation for SUPER SIGNALS (>30.0) ---
            # If the signal is extremely strong (e.g. Pump/Breakout), ignore correlation.
            is_super_signal = (signal.score >= 30.0)
            
            if is_super_signal:
                log(f"🚀 SUPER SIGNAL DETECTED ({signal.score}): Bypassing Correlation Check for {symbol}")
            else:
                is_correlated = False
                for held_symbol in self.executor.paper_positions:
                    if held_symbol == symbol: continue
                    try:
                        held_candles = await self.loader.get_ohlcv(held_symbol, timeframe='1h', limit=50)
                        if held_candles:
                            corr = self.analyzer.calculate_correlation(candles, held_candles)
                            if corr > 0.85:
                                log(f"🔗 Correlation Alert: {symbol} is highly correlated with held {held_symbol} ({corr:.2f}). Skipping.")
                                self.executor.brain.record_ghost_trade(
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
                    return None
                
        return signal

    async def _check_risk_management(self, symbol, candles, current_price):
        """Checks for StopLoss/TakeProfit conditions"""
        if symbol in self.executor.paper_positions:
            df_candles = None
            if candles:
                 try:
                     df_candles = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                     for c in ['open', 'high', 'low', 'close', 'volume']:
                         df_candles[c] = df_candles[c].astype(float)
                 except Exception as e:
                     log(f"⚠️ Risk Data Prep Error ({symbol}): {e}")
            
            risk_check = self.executor.check_risk_conditions(symbol, current_price, df_candles)
            action = risk_check.get('action')
            
            if action in ['CLOSE', 'PARTIAL_CLOSE']:
                reason = risk_check.get('reason', 'RISK_EXIT')
                
                # BNB PROTECTION: Do not score -100 for BNB
                if symbol == "BNB/USDT":
                     log(f"🛡️ Risk Exit Triggered for BNB/USDT but suppressed (Base Asset Protection). Reason: {reason}")
                     return None
                
                log(f"🛡️ Risk Exit Triggered [{symbol}]: {action} - {reason}")
                
                signal_action = "EXIT" if action == 'CLOSE' else "PARTIAL_EXIT"
                score = -100.0 if action == 'CLOSE' else 100.0
                
                return TradeSignal(
                    symbol=symbol,
                    action=signal_action,
                    direction="LONG",
                    score=score,
                    estimated_yield=0.0,
                    timestamp=int(time.time() * 1000),
                    details={
                        "reason": reason, 
                        "close": current_price,
                        "qty_pct": risk_check.get('qty_pct', 1.0)
                    }
                )
        return None

    async def handle_sniper_mode(self, all_market_signals: List[TradeSignal], current_prices_map: Dict):
        """Executes the Sniper Mode (Low Balance) logic"""
        log(f"⚠️ Düşük Bakiye Modu Aktif (Sniper Modu Devrede!)")
        
        # 1. En iyi sinyali bul
        high_quality_signals = sorted([
            s for s in all_market_signals 
            if s.action == 'ENTRY' and s.score >= 0.75
        ], key=lambda x: x.score, reverse=True)
        
        best_signal = None
        if not high_quality_signals:
            if [s for s in all_market_signals if s.action == 'ENTRY']:
                 log("⏳ Sniper Modu: Giriş sinyalleri var ama yeterince güçlü değil (<0.75). Nakitte bekleniyor...")
        else:
            best_signal = high_quality_signals[0]
            # Futures Sentiment Check
            if self.sentiment_analyzer:
                try:
                    futures_data = await self.sentiment_analyzer.get_futures_sentiment(best_signal.symbol)
                    ls_ratio = futures_data.get('long_short_ratio', 0)
                    if ls_ratio > 2.5:
                         log(f"⚠️ DİKKAT: {best_signal.symbol} aşırı Long yığılması (Ratio: {ls_ratio}).")
                except Exception as e:
                    log(f"⚠️ Futures Check Failed: {e}")

        # 2. Mevcut Pozisyonları Yönet
        current_positions = list(self.executor.paper_positions.keys())
        made_swap = False
        for symbol in current_positions:
            should_sell = False
            fast_path = False
            
            # Durum A: En iyi sinyal var ama elimizdeki o değil
            if best_signal and symbol != best_signal.symbol:
                current_pos_signal = next((s for s in all_market_signals if s.symbol == symbol), None)
                current_score = current_pos_signal.score if current_pos_signal else 0.0 # TODO: use cache if needed
                
                score_diff = best_signal.score - current_score
                
                # --- PRO UPDATE: Adaptive Sniper Threshold ---
                # Piyasada volatilite yüksekse fark 5.0 kalsın, düşükse 3.5'e insin.
                # Volatilite bilgisini en iyi sinyalden alabiliriz
                current_vol = 0.0
                if best_signal.details:
                    current_vol = best_signal.details.get('volatility', 0.0)
                
                required_diff = 5.0
                if current_vol < 1.0: # Düşük Volatilite (<%1)
                    required_diff = 3.5
                
                # --- FAST PATH: Super Signal with wide lead (>=20) ---
                fast_threshold = 31.0 if best_signal.symbol == 'ZAMA/USDT' else 32.0
                if best_signal.score >= fast_threshold and score_diff >= 20.0:
                    fast_path = True
                    should_sell = True
                    log(f"⚡ Sniper Fast Path: Selling {symbol} immediately (Super {best_signal.symbol} {best_signal.score:.1f}, Δ={score_diff:.1f}≥20)")
                    self.swap_confirmation_tracker[symbol] = 0
                elif score_diff >= required_diff:
                    current_count = self.swap_confirmation_tracker.get(symbol, 0) + 1
                    self.swap_confirmation_tracker[symbol] = current_count
                    
                    if current_count >= 3:
                        should_sell = True
                        log(f"📉 Sniper Modu: {symbol} satılıyor. (Fark: {score_diff:.1f} >= {required_diff})")
                        self.swap_confirmation_tracker[symbol] = 0
                    else:
                        log(f"⏳ Sniper Modu: {symbol} swap onayı ({current_count}/3). Fark: {score_diff:.1f}")
                else:
                    self.swap_confirmation_tracker[symbol] = 0
                    log(f"✋ Sniper Modu: {symbol} tutuluyor. Fark yetersiz ({score_diff:.1f} < {required_diff}).")
            
            # Durum B: Çoklu pozisyon varsa sat (Tekilleştirme)
            elif len(current_positions) > 1:
                should_sell = True
                log(f"📉 Sniper Modu: Portföy tekilleştiriliyor. {symbol} satılıyor.")
                
            if should_sell:
                await self._execute_sell(symbol, current_prices_map, reason="SNIPER_MODE_LIQUIDATION")
                if best_signal and symbol != best_signal.symbol:
                    made_swap = True

        # 2.5 Dust Temizliği
        if not settings.IS_TR_BINANCE:
             log("🧹 Sniper Modu: Dust Temizliği...")
             await self.executor.convert_dust_to_bnb()
             await self.executor.sync_wallet_balances()
             
             # BNB Satışı (Eğer hedef BNB değilse)
             if best_signal and not best_signal.symbol.startswith('BNB'):
                 if 'BNB/USDT' in self.executor.paper_positions:
                     await self._execute_sell('BNB/USDT', current_prices_map, reason="SNIPER_MODE_BNB_LIQUIDATION")

        # Satışlardan sonra bakiyeyi ve pozisyonları senkronize et
        await self.executor.sync_wallet_balances()

        # 3. Alım Yap (Tek Atış)
        can_buy = False
        pos_count = len(self.executor.paper_positions)
        if pos_count == 0:
            can_buy = True
        elif pos_count == 1 and best_signal and best_signal.symbol in self.executor.paper_positions:
            can_buy = False
            log(f"🎯 Zaten hedef varlıktayız: {best_signal.symbol}")
        else:
            # Sniper Modu: Açık pozisyon varsa önce likide et, sonra alım yap
            can_buy = False
            log("⏳ Sniper: Satış sonrası bakiye güncellemesi bekleniyor, alım ertelendi.")
        if made_swap and best_signal:
            can_buy = True

        if can_buy and best_signal:
            try:
                # --- SAFETY: Re-validate before buy (best-effort) ---
                try:
                    if (not settings.USE_MOCK_DATA) or (best_signal.score >= 31.0 or best_signal.symbol == 'ZAMA/USDT'):
                        # 1) Price slippage check vs. last seen price
                        last_seen = current_prices_map.get(best_signal.symbol, 0.0)
                        candles_now = await self.loader.get_ohlcv(best_signal.symbol, timeframe='1h', limit=10)
                        if candles_now:
                            current_px = float(candles_now[-1][4])
                            if last_seen > 0.0:
                                slip = abs(current_px - last_seen) / last_seen
                                if slip > 0.01:
                                    log(f"⛔ Slippage >1% for {best_signal.symbol} (ref={last_seen}, now={current_px}). Aborting sniper buy.")
                                    return
                        # 2) Re-validate minimum score threshold
                        reval_threshold = 0.75
                        if best_signal.score >= 31.0 or best_signal.symbol == 'ZAMA/USDT':
                            reval_threshold = 31.0 if best_signal.symbol == 'ZAMA/USDT' else 32.0
                        if best_signal.score < reval_threshold:
                            log(f"⛔ Super signal weakened (<32). Aborting sniper buy for {best_signal.symbol}.")
                            return
                except Exception:
                    pass
                
                log(f"🎯 Sniper Modu: {best_signal.symbol} için tam bakiye ile giriş yapılıyor!")
                if best_signal.details is None: best_signal.details = {}
                best_signal.details['force_all_in'] = True
                await self.executor.execute_strategy(best_signal)
            except InsufficientBalanceError as e:
                log(f"❌ Sniper Alım Başarısız (Yetersiz Bakiye): {e}")
            except ExchangeError as e:
                log(f"❌ Sniper Alım Başarısız (Borsa Hatası): {e}")
            except Exception as e:
                log(f"❌ Sniper Alım Beklenmedik Hata: {e}")

    async def _execute_sell(self, symbol, current_prices_map, reason):
        """Helper to execute sell, handling Dust conversion automatically"""
        price = current_prices_map.get(symbol, 0.0)
        if price == 0.0:
            price = self.executor.paper_positions.get(symbol, {}).get('entry_price', 0.0)
        
        pos_qty = self.executor.paper_positions.get(symbol, {}).get('quantity', 0.0)
        value_est = pos_qty * price
        
        if 0.0 < value_est < 6.0 and not settings.IS_TR_BINANCE:
            log(f"🧹 {symbol} Dust Convert'e yönlendiriliyor.")
            await self.executor.convert_dust_to_bnb()
            await asyncio.sleep(1.0)
            return

        sell_signal = TradeSignal(
            symbol=symbol,
            action="EXIT",
            direction="LONG",
            score=-10.0,
            estimated_yield=0.0,
            timestamp=int(time.time() * 1000),
            details={"reason": reason, "close": price}
        )
        await self.executor.execute_strategy(sell_signal)
        
        # --- CRITICAL FIX: Wait for Balance Update ---
        log("⏳ Waiting 5 seconds for balance update after SELL...")
        await asyncio.sleep(5.0)
        await self.executor.sync_wallet_balances()

    async def handle_normal_swap_logic(self, all_market_signals):
        """Executes the Normal Mode Swap logic"""
        if self.executor.paper_positions and all_market_signals:
            swap_opp = self.opportunity_manager.check_for_swap_opportunity(
                self.executor.paper_positions, 
                all_market_signals
            )
            
            if swap_opp:
                sell_symbol = swap_opp['sell_symbol']
                buy_symbol = swap_opp['buy_signal'].symbol
                
                current_count = self.swap_confirmation_tracker.get(sell_symbol, 0) + 1
                self.swap_confirmation_tracker[sell_symbol] = current_count
                
                if current_count >= 3:
                    log(f"🔄 SWAP CONFIRMED: Sell {sell_symbol} -> Buy {buy_symbol}")
                    
                    try:
                        # 1. Sell
                        sell_signal = TradeSignal(
                            symbol=sell_symbol,
                            action="EXIT",
                            direction="LONG",
                            score=-1.0,
                            estimated_yield=0.0,
                            timestamp=int(time.time() * 1000),
                            details={"reason": "SWAP_FOR_BETTER_OPPORTUNITY"}
                        )
                        await self.executor.execute_strategy(sell_signal)
                        
                        # 2. Buy
                        await asyncio.sleep(2.0) 
                        await self.executor.sync_wallet_balances()
                        await self.executor.execute_strategy(swap_opp['buy_signal'])
                        
                        self.swap_confirmation_tracker[sell_symbol] = 0
                    except (InsufficientBalanceError, ExchangeError) as e:
                        log(f"❌ Swap İşlemi Başarısız: {e}")
                    except Exception as e:
                        log(f"❌ Swap İşlemi Beklenmedik Hata: {e}")
                else:
                    log(f"⏳ Swap Opportunity Detected: {sell_symbol} -> {buy_symbol}. Waiting ({current_count}/3)...")
            else:
                if self.swap_confirmation_tracker:
                    self.swap_confirmation_tracker.clear()
