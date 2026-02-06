import time
import logging
import pandas as pd
import asyncio
import math
from datetime import datetime
from typing import Dict, Optional, Union, List, Any
from binance.error import ClientError
from src.utils.logger import log
from src.utils.state_manager import StateManager
from src.learning.brain import BotBrain
from src.strategies.analyzer import TradeSignal
from src.execution.stop_loss_manager import StopLossManager
from src.execution.position_sizer import DynamicPositionSizer
from config.settings import settings

class BinanceExecutor:
    def __init__(self, exchange_client=None, is_tr=False):
        self.exchange_spot = exchange_client
        self.is_tr = is_tr
        self.is_live = settings.LIVE_TRADING
        self.state_manager = StateManager()
        self.brain = BotBrain()
        
        # State yükle
        loaded_state = self.state_manager.load_state()
        
        # State Migration: Eğer 'paper_positions' anahtarı yoksa ve state doluysa, eski düz (flat) yapıdadır.
        if loaded_state and 'paper_positions' not in loaded_state:
            # Muhtemelen eski format (direkt pozisyonlar root'ta)
            # Sadece dict olan ve fiyat bilgisi içerenleri pozisyon kabul et
            legacy_positions = {}
            for k, v in loaded_state.items():
                if isinstance(v, dict) and ('entry_price' in v or 'price' in v or 'quantity' in v):
                    legacy_positions[k] = v
            
            self.full_state = {
                'paper_positions': legacy_positions,
                'wallet_assets': {},
                'total_balance': 0.0,
                'is_live': self.is_live
            }
            log("⚠️ State dosyası eski formatta, yeni yapıya dönüştürüldü.")
        else:
            self.full_state = loaded_state if loaded_state else {'paper_positions': {}, 'wallet_assets': {}, 'total_balance': 0.0}

        self.paper_positions = self.full_state.get('paper_positions', {})
        self.order_history = self.full_state.get('order_history', [])
        # Paper Trading Balance
        self.paper_balance = self.full_state.get('paper_balance', settings.PAPER_TRADING_BALANCE)
        
        self.stats = self.state_manager.load_stats()
        self.initialize_daily_stats()
        
        # Emir takibi
        self.active_orders = {}
        
        # Risk yönetimi
        self.max_daily_loss = settings.MAX_DAILY_LOSS_PCT
        self.emergency_stop = False
        
        # Stop Loss Manager (Phase 1 Integration)
        self.stop_loss_manager = StopLossManager()
        
        # Position Sizer (Phase 2 Integration)
        self.position_sizer = DynamicPositionSizer()
        
        # Min Trade Amount Configuration
        # Global / USDT Mode
        self.min_trade_amount = 6.0 # USDT (Binance min usually $5)
            
        log(f"Executor başlatıldı. Mod: {'CANLI' if self.is_live else 'KAĞIT'} | Min İşlem: {self.min_trade_amount} USDT")

    def save_positions(self):
        """Pozisyonları state dosyasına kaydet"""
        self.full_state['paper_positions'] = self.paper_positions
        self.full_state['order_history'] = self.order_history
        self.full_state['is_live'] = self.is_live
        self.full_state['paper_balance'] = self.paper_balance
        
        # Update total balance for dashboard if not live
        if not self.is_live:
             total_pos_value = 0.0
             for sym, pos in self.paper_positions.items():
                 total_pos_value += pos['quantity'] * pos['entry_price']
             self.full_state['total_balance'] = self.paper_balance + total_pos_value

        self.state_manager.save_state(self.full_state)

    def update_commentary(self, commentary: Dict[str, Any]):
        """Bot yorumlarını state dosyasına kaydet"""
        self.full_state['commentary'] = commentary
        self.state_manager.save_state(self.full_state)

    async def initialize(self):
        """Async initialization"""
        log("Executor initialized async.")
        
        # Futures Setup
        if not self.is_tr and settings.TRADING_MODE == 'futures' and self.exchange_spot:
             try:
                 log(f"⚙️ Futures Ayarları Yapılandırılıyor (Kaldıraç: {settings.LEVERAGE}x)...")
                 # Set Leverage for all symbols in settings
                 # Note: This might take time if list is long. Maybe do it on demand or for top symbols?
                 # For now, we do it for monitored symbols if possible, or lazy load.
                 # Actually, binance requires setting leverage per symbol.
                 # We will do it lazily in execute_buy/sell or here for initial list.
                 # Let's do it for the current settings.SYMBOLS
                 for symbol in settings.SYMBOLS:
                     try:
                         # Normalize symbol for CCXT (BTC/USDT)
                         # settings.SYMBOLS might be BTC_TRY or BTC/USDT.
                         # If TR, it's BTC_TRY. If Global, likely BTC/USDT.
                         # We assume symbols are correct for the mode.
                         await asyncio.to_thread(self.exchange_spot.set_leverage, settings.LEVERAGE, symbol)
                     except Exception as e:
                         # Ignore symbol errors (might be invalid symbol)
                         pass
                 log("✅ Kaldıraç ayarlandı.")
             except Exception as e:
                 log(f"⚠️ Kaldıraç ayarlama hatası: {e}")

        if self.is_live:
             await self.sync_wallet_balances()

    async def sync_wallet_balances(self):
        """Gerçek cüzdan bakiyelerini state'e senkronize et"""
        if not self.is_live or not self.exchange_spot:
            log(f"DEBUG: Skipping wallet sync. Live: {self.is_live}, Client: {self.exchange_spot}")
            return

        try:
            # Binance TR senkron çağrı
            if self.is_tr:
                # BinanceTRClient uses get_account_info
                balance_data = await asyncio.to_thread(self.exchange_spot.get_account_info)
            else:
                # Global için ccxt fetch_balance
                balance_data = await asyncio.to_thread(self.exchange_spot.fetch_balance)

            wallet_assets = {}
            total_try_balance = 0.0

            if self.is_tr:
                # TR API Parsing
                balances = []
                if isinstance(balance_data, dict):
                    # Check for 'data' wrapper from BinanceTRClient
                    data = balance_data.get('data')
                    if isinstance(data, dict) and 'accountAssets' in data:
                         balances = data['accountAssets']
                    elif isinstance(data, list):
                         balances = data
                    elif 'balances' in balance_data:
                         balances = balance_data['balances']
                elif isinstance(balance_data, list):
                    balances = balance_data
                
                for b in balances:
                    asset = b.get('asset')
                    free = float(b.get('free', 0.0))
                    locked = float(b.get('locked', 0.0))
                    total = free + locked
                    
                    if total > 0:
                        wallet_assets[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
                        if asset == 'TRY':
                            total_try_balance = total
            else:
                # Global (CCXT) Parsing
                # CCXT genelde {'total': {'BTC': 0.1, ...}, 'free': {...}} döner
                total_balances = balance_data.get('total', {})
                free_balances = balance_data.get('free', {})
                locked_balances = balance_data.get('used', {})
                
                for asset, amount in total_balances.items():
                    if amount > 0:
                        wallet_assets[asset] = {
                            'free': free_balances.get(asset, 0.0),
                            'locked': locked_balances.get(asset, 0.0),
                            'total': amount
                        }
                        if asset == 'USDT': # Globalde ana para birimi genelde USDT
                            total_try_balance = amount # Değişken adı try kalsa da globalde usdt tutar

            # State'e kaydet
            self.full_state['wallet_assets'] = wallet_assets
            self.full_state['total_balance'] = total_try_balance
            
            # --- Auto-Import Existing Assets to Bot Positions ---
            if self.is_live:
                await self._import_wallet_to_positions(wallet_assets)

            self.save_positions()
            log(f"💰 Cüzdan Senkronize: {len(wallet_assets)} varlık bulundu. Bakiye: {total_try_balance:.2f}")

        except Exception as e:
            log(f"⚠️ Cüzdan senkronizasyon hatası: {e}")

    async def _import_wallet_to_positions(self, wallet_assets: dict):
        """
        Cüzdandaki varlıkları (bot tarafından alınmamış olsa bile) pozisyonlara ekler.
        Böylece bot bu varlıkları da yönetebilir (Satış sinyali gelirse satabilir).
        """
        try:
            for asset, data in wallet_assets.items():
                if asset == 'TRY': continue
                
                # Sembol ismini oluştur (örn: AVAX -> AVAX_TRY)
                symbol = f"{asset}_TRY"
                
                # Bu varlık zaten pozisyonlarımızda var mı?
                if symbol in self.paper_positions:
                    continue
                
                # Bu varlık işlem yaptığımız semboller listesinde mi?
                # (settings.SYMBOLS listesine erişim gerekebilir, şimdilik main'den gelen listeyi varsayalım veya tümünü alalım)
                # Güvenlik için sadece bilinen sembolleri ekle
                # Ancak settings modülü import edilmiş durumda
                if hasattr(settings, 'SYMBOLS') and symbol not in settings.SYMBOLS:
                     continue

                free_amount = data.get('free', 0.0)
                if free_amount <= 0: continue

                # Güncel fiyatı al (Değer kontrolü ve entry_price için)
                current_price = 0.0
                try:
                    ticker = await asyncio.to_thread(self.exchange_spot.fetch_ticker, symbol)
                    current_price = float(ticker['last'])
                except:
                    continue # Fiyat alınamazsa atla

                if current_price <= 0: continue

                # Minimum değer kontrolü (Örn: 50 TRY altı "dust" sayılır, işlem yapılamaz)
                total_value = free_amount * current_price
                if total_value < 50.0:
                    continue

                # Pozisyonu ekle
                log(f"🎒 Cüzdanda mevcut varlık tespit edildi: {symbol} ({free_amount} adet, ~{total_value:.2f} TRY). Bota dahil ediliyor.")
                self.paper_positions[symbol] = {
                    'entry_price': current_price, # Maliyeti bilmediğimiz için güncel fiyatı baz alıyoruz
                    'quantity': free_amount,
                    'timestamp': time.time(),
                    'highest_price': current_price,
                    'is_imported': True # Sonradan eklendiğini belirtmek için flag
                }

        except Exception as e:
            log(f"⚠️ Varlık import hatası: {e}")

    def initialize_daily_stats(self):
        """Günlük istatistikleri başlattır/sıfırla"""
        if 'daily_realized_pnl' not in self.stats:
            self.stats['daily_realized_pnl'] = 0.0
        if 'daily_trade_count' not in self.stats:
            self.stats['daily_trade_count'] = 0
        if 'total_pnl_pct' not in self.stats:
            self.stats['total_pnl_pct'] = 0.0
        if 'total_trades' not in self.stats:
            self.stats['total_trades'] = 0
        if 'win_rate' not in self.stats:
            self.stats['win_rate'] = 0.0

    async def get_free_balance(self, asset: str = 'TRY') -> float:
        """Kullanılabilir (Free) bakiyeyi getir"""
        try:
            if not self.is_live:
                # Paper trading için sanal bakiyeyi kullan
                if asset in ['TRY', 'USDT']: # Quote currency
                     return self.paper_balance
                return 0.0

            if self.is_tr:
                if not self.exchange_spot: return 0.0
                
                # Cache veya senkron çağrı ile bakiye
                # Performans için state'deki son wallet_assets'i kullanabiliriz
                # Ama anlık kontrol için API çağrısı daha güvenli
                balance_data = await asyncio.to_thread(self.exchange_spot.get_account_info)
                
                balances = []
                if isinstance(balance_data, dict):
                    data = balance_data.get('data', balance_data)
                    if isinstance(data, dict):
                        balances = data.get('accountAssets', data.get('balances', []))
                    elif isinstance(data, list):
                        balances = data
                elif isinstance(balance_data, list):
                    balances = balance_data

                for b in balances:
                    if b.get('asset') == asset:
                        return float(b.get('free', 0.0))
                return 0.0
            else:
                if not self.exchange_spot: return 0.0
                balance = await asyncio.to_thread(self.exchange_spot.fetch_balance)
                return float(balance.get('free', {}).get('USDT' if asset == 'TRY' else asset, 0.0))

        except Exception as e:
            log(f"⚠️ Free Bakiye hatası: {e}")
            return 0.0

    async def get_total_balance(self) -> float:
        """Toplam bakiyeyi hesapla (USDT/TRY)"""
        try:
            if not self.is_live:
                # Kağıt işlem bakiyesi: Nakit + Pozisyon Değerleri (yaklaşık)
                # Basitlik için sadece nakit bakiyeyi ve realized PnL'yi takip ediyoruz
                # Ancak pozisyon büyüklüğü hesaplanırken toplam varlık önemli
                
                # Pozisyonların güncel değerini ekle
                total_pos_value = 0.0
                for sym, pos in self.paper_positions.items():
                    # Giriş fiyatını baz al (güncel fiyatı o an bilmiyor olabiliriz)
                    # Daha doğrusu için o anki fiyatı çekmek lazım ama burası için maliyet bazlı gidelim
                    total_pos_value += pos['quantity'] * pos['entry_price']
                
                return self.paper_balance + total_pos_value
            
            if self.is_tr:
                if not self.exchange_spot:
                    return 0.0
                # Binance TR senkron çağrı, thread içinde çalıştır
                # FIX: get_balance yerine get_account_info kullan
                balance_data = await asyncio.to_thread(self.exchange_spot.get_account_info)
                if not balance_data:
                    return 0.0
                    
                # TR API yapısına göre parse et
                balances = []
                if isinstance(balance_data, list):
                    balances = balance_data
                elif isinstance(balance_data, dict):
                    # Check for 'data' wrapper from BinanceTRClient
                    data = balance_data.get('data')
                    if isinstance(data, dict) and 'accountAssets' in data:
                         balances = data['accountAssets']
                    elif isinstance(data, list):
                         balances = data
                    elif 'balances' in balance_data:
                         balances = balance_data['balances']
                
                for b in balances:
                    if b.get('asset') == 'TRY':
                        return float(b.get('free', 0.0)) + float(b.get('locked', 0.0))
                
                return 0.0
            else:
                # Global Binance (ccxt benzeri yapı varsayımı)
                if not self.exchange_spot:
                    return 0.0
                balance = await asyncio.to_thread(self.exchange_spot.fetch_balance)
                return float(balance.get('total', {}).get('USDT', 0.0))
        except Exception as e:
            log(f"⚠️ Bakiye hesaplama hatası: {e}")
            return 0.0

    async def calculate_quantity(self, symbol: str, price: float, side: str, risk_score: float = 10.0, atr_value: float = 0.0, regime: str = 'NEUTRAL') -> float:
        """İşlem miktarını hesapla (Dinamik Risk Yönetimi + Volatilite Bazlı + Market Rejimi - Phase 3)"""
        try:
            balance = await self.get_total_balance()
            if balance <= 0:
                return 0.0
                
            # Phase 2 & 3: Volatility & Regime Based Position Sizing
            if atr_value > 0 and price > 0:
                # 1. Volatilite ve Rejim Parametrelerini Hesapla
                params = self.position_sizer.calculate_params_from_atr(symbol, atr_value, price, balance, regime)
                
                target_leverage = params['leverage']
                position_cost = params['position_cost_usdt']
                
                # 2. Kaldıracı Ayarla (Sadece Futures ve Canlı ise)
                if self.is_live and not self.is_tr and settings.TRADING_MODE == 'futures':
                    try:
                        # Mevcut kaldıracı kontrol etmek pahalı olabilir, direkt set ediyoruz
                        log(f"⚙️ Kaldıraç Ayarlanıyor ({symbol}): {target_leverage}x (Volatilite: %{params['volatility_pct']:.2f})")
                        await asyncio.to_thread(self.exchange_spot.set_leverage, target_leverage, symbol)
                    except Exception as e:
                        log(f"⚠️ Kaldıraç ayarlama hatası: {e}")
                
                # 3. Miktarı Hesapla (Notional = Cost * Leverage)
                # Not: Binance Futures için 'quantity' genellikle coin cinsindendir (BTC).
                # Cost (Margin) = (Quantity * Price) / Leverage
                # Quantity = (Cost * Leverage) / Price
                
                target_position_size_usdt = position_cost * target_leverage
                
                # Güvenlik: Risk Skoruna göre ölçekle (Opsiyonel ama iyi bir pratik)
                confidence_factor = max(0.2, min(1.0, risk_score / 10.0))
                target_position_size_usdt *= confidence_factor
                
                log(f"⚖️ Pozisyon Hesaplama (Phase 2): Bakiye={balance:.2f} | Risk={params['risk_level']} | Kaldıraç={target_leverage}x | Hedef Notional={target_position_size_usdt:.2f}")

            else:
                # Fallback: Eski Mantık (ATR yoksa)
                base_pct = settings.MAX_POSITION_PCT / 100.0
                confidence_factor = max(0.2, min(1.0, risk_score / 10.0))
                target_position_size_usdt = balance * base_pct * confidence_factor # Bu notional mı margin mi? Eski kodda margin gibi kullanılıyordu (Lev=1 varsayımı ile)
                if not self.is_tr and settings.TRADING_MODE == 'futures':
                     # Eğer futures ise ve ATR yoksa varsayılan kaldıraçla notional hesapla
                     target_position_size_usdt *= settings.LEVERAGE 
                
                log(f"⚖️ Pozisyon Hesaplama (Fallback): Bakiye={balance:.2f} | Baz=%{base_pct*100} | Hedef={target_position_size_usdt:.2f}")

            
            # Minimum İşlem Tutarı Kontrolü
            min_trade_val = self.min_trade_amount
            
            # Eğer hesaplanan tutar min limitin altındaysa ve bakiye yetiyorsa yükselt
            if target_position_size_usdt < min_trade_val:
                # Bakiyemiz min tutarı karşılıyor mu? (Komisyon payı ile)
                # Not: Futures için margin kontrolü gerekir. Margin = Notional / Leverage
                required_margin = min_trade_val / (target_leverage if 'target_leverage' in locals() else settings.LEVERAGE)
                
                if balance >= (required_margin * 1.05): 
                    target_position_size_usdt = min_trade_val * 1.05
            
            # Güvenlik: Asla toplam bakiyeden (kaldıraçlı) fazla işlem açma
            # Max Notional = Balance * Leverage * 0.98
            current_leverage = target_leverage if 'target_leverage' in locals() else settings.LEVERAGE
            max_safe_notional = balance * current_leverage * 0.98
            
            if target_position_size_usdt > max_safe_notional:
                target_position_size_usdt = max_safe_notional
            
            # Son kontrol
            if target_position_size_usdt < min_trade_val:
                return 0.0
            
            quantity = target_position_size_usdt / price
            
            # Filtreleri uygula (stepSize, minQty)
            if self.is_live and self.exchange_spot:
                symbol_info = await self.get_symbol_info(symbol)
                if symbol_info:
                    step_size = float(symbol_info.get('stepSize', '1.0'))
                    min_qty = float(symbol_info.get('minQty', '0.0'))
                    
                    # Precision ayarla
                    if step_size > 0:
                        precision = int(round(-math.log10(step_size)))
                        quantity = round(quantity, precision)
                    else:
                        quantity = int(quantity)
                    
                    if quantity < min_qty:
                        return 0.0
                        
            return quantity
        except Exception as e:
            log(f"Miktar hesaplama hatası: {e}")
            return 0.0

    async def get_symbol_info(self, symbol: str):
        """Sembol bilgilerini al (filtreler için)"""
        try:
            if self.is_tr:
                response = await asyncio.to_thread(self.exchange_spot.get_exchange_info)
                
                # Wrapper kontrolü (BinanceTRClient {"code": 0, "data": ...} döner)
                data = response
                if isinstance(response, dict) and 'data' in response:
                    data = response['data']
                
                # Parse info to find symbol
                if data and 'symbols' in data:
                    target_symbol = symbol.replace('_', '')
                    for s in data['symbols']:
                        # Global API sembolleri '_' içermez (BTCUSDT)
                        if s['symbol'] == target_symbol:
                            # Filtreleri bul
                            filters = {f['filterType']: f for f in s['filters']}
                            lot_size = filters.get('LOT_SIZE', {})
                            price_filter = filters.get('PRICE_FILTER', {})
                            return {
                                'stepSize': lot_size.get('stepSize', '1.0'),
                                'minQty': lot_size.get('minQty', '0.0'),
                                'tickSize': price_filter.get('tickSize', '0.01')
                            }
            else:
                # Global / CCXT
                if self.exchange_spot:
                    if not self.exchange_spot.markets:
                        await asyncio.to_thread(self.exchange_spot.load_markets)
                    
                    if symbol in self.exchange_spot.markets:
                        market = self.exchange_spot.markets[symbol]
                        # CCXT stores precision as float usually
                        return {
                            'stepSize': str(market['precision'].get('amount', 1.0)),
                            'minQty': str(market['limits']['amount'].get('min', 0.0)),
                            'tickSize': str(market['precision'].get('price', 0.01))
                        }
            return None
        except Exception as e:
            log(f"Sembol bilgi hatası: {e}")
            return None

    async def execute_strategy(self, signals: Union[pd.DataFrame, TradeSignal, List[TradeSignal]], latest_scores: Dict[str, float] = None):
        """Sinyalleri işle"""
        # Günlük zarar limiti kontrolü
        if self.stats.get('daily_realized_pnl', 0) < -(self.max_daily_loss):
            if not self.emergency_stop:
                log(f"🛑 GÜNLÜK ZARAR LİMİTİ AŞILDI (%{self.max_daily_loss}). İşlemler durduruluyor.")
                self.emergency_stop = True
            return

        # Normalize input to a list of signals or rows
        if isinstance(signals, TradeSignal):
            signal_items = [signals]
        elif isinstance(signals, list):
            signal_items = signals
        elif isinstance(signals, pd.DataFrame):
            # Legacy DataFrame support
            for _, row in signals.iterrows():
                symbol = row['symbol']
                signal = row['signal']
                price = row['close']
                
                current_pos = self.paper_positions.get(symbol)
                
                if signal == 1:  # AL Sinyali
                    if not current_pos:
                        qty = await self.calculate_quantity(symbol, price, 'BUY', risk_score=5.0) # Legacy için orta risk
                        if qty > 0:
                            await self.execute_buy(symbol, qty, price)
                elif signal == -1:  # SAT Sinyali
                    if current_pos:
                        qty = current_pos['quantity']
                        await self.execute_sell(symbol, qty, price, current_pos)
            return
        else:
            log(f"⚠️ Geçersiz sinyal formatı: {type(signals)}")
            return

        # Process TradeSignal objects
        for sig in signal_items:
            symbol = sig.symbol
            action = sig.action
            price = sig.details.get('close', 0.0)
            
            # Mevcut pozisyon var mı?
            current_pos = self.paper_positions.get(symbol)
            
            if action == "ENTRY":
                if not current_pos:
                    # Score varsa kullan, yoksa varsayılan 10 (maksimum)
                    score = sig.score if hasattr(sig, 'score') else 10.0
                    
                    # --- SMART SWAP LOGIC START ---
                    # Yetersiz bakiye durumunda düşük puanlı varlığı satıp buna geçme kontrolü
                    base_asset = 'TRY' if self.is_tr else 'USDT'
                    free_balance = await self.get_free_balance(base_asset)
                    min_trade_val = self.min_trade_amount
                    
                    if free_balance < min_trade_val and latest_scores:
                        log(f"📉 Yetersiz Bakiye ({free_balance:.2f} {base_asset}). Swap fırsatı aranıyor...")
                        
                        worst_symbol = None
                        worst_score = 999.0
                        
                        # Elimdeki pozisyonları tara
                        for pos_sym in list(self.paper_positions.keys()):
                            # Eğer şu anki aday sembol zaten elimizdeyse geç (mantıken buraya girmemeli ama check)
                            if pos_sym == symbol: continue
                            
                            # Pozisyonun güncel skorunu bul
                            current_score = latest_scores.get(pos_sym)
                            
                            # Eğer güncel skor yoksa, bu sembol henüz taranmamış olabilir.
                            # Varsayılan olarak yüksek ver ki yanlışlıkla satmayalım
                            if current_score is None:
                                continue
                                
                            if current_score < worst_score:
                                worst_score = current_score
                                worst_symbol = pos_sym
                        
                        # Swap Kararı: Yeni aday, en kötüden %20 daha iyiyse
                        if worst_symbol and score > (worst_score * 1.2):
                            log(f"♻️ SWAP FIRSATI: {worst_symbol} (Skor: {worst_score:.1f}) -> {symbol} (Skor: {score:.1f})")
                            log(f"🚀 {worst_symbol} satılıyor ve bakiye {symbol} için kullanılacak.")
                            
                            # Satış yap
                            pos_data = self.paper_positions.get(worst_symbol)
                            if pos_data:
                                # Satılacak coinin güncel fiyatını al (PnL hesabı için)
                                current_sell_price = pos_data.get('entry_price', 0.0)
                                try:
                                    if self.exchange_spot:
                                        ticker = await asyncio.to_thread(self.exchange_spot.fetch_ticker, worst_symbol)
                                        current_sell_price = float(ticker['last'])
                                except Exception as e:
                                    log(f"⚠️ Fiyat alma hatası ({worst_symbol}): {e}")

                                sell_success = await self.execute_sell(worst_symbol, pos_data['quantity'], current_sell_price, pos_data)
                                
                                # Eğer satış başarısızsa alımı yapma!
                                if not sell_success:
                                    log(f"🛑 Satış başarısız olduğu için Swap iptal edildi: {worst_symbol}")
                                    continue
                                
                                # Bakiyenin güncellenmesi için kısa bekleme
                                await asyncio.sleep(2.0)
                        else:
                            if worst_symbol:
                                log(f"✋ Swap yapılmadı. En kötü {worst_symbol} ({worst_score:.1f}) vs Aday ({score:.1f}). Fark yetersiz.")
                            else:
                                log("✋ Swap yapılamadı. Uygun aday bulunamadı.")
                    
                    # --- SMART SWAP LOGIC END ---
                    
                    # Phase 3 Update: Pass Regime Info
                    atr_val = float(sig.details.get('ATR', 0.0))
                    regime = sig.details.get('regime', 'NEUTRAL')
                    qty = await self.calculate_quantity(symbol, price, 'BUY', risk_score=score, atr_value=atr_val, regime=regime)
                    if qty > 0:
                        await self.execute_buy(symbol, qty, price, features=sig.details)
                        
            elif action == "EXIT" or action == "PARTIAL_EXIT":
                if current_pos:
                    qty = current_pos['quantity']
                    is_partial = False
                    
                    if action == "PARTIAL_EXIT":
                        is_partial = True
                        qty_pct = sig.details.get('qty_pct', 0.5)
                        qty = qty * qty_pct
                        log(f"🌗 Kısmi Çıkış Sinyali: %{qty_pct*100} oranında satış.")
                        
                    await self.execute_sell(symbol, qty, price, current_pos, is_partial=is_partial)

    async def execute_buy(self, symbol: str, quantity: float, price: float, features: dict = None) -> bool:
        """Alım emri"""
        log(f"🟢 ALIŞ Sinyali: {symbol} - Fiyat: {price} - Miktar: {quantity}")
        
        # Min Notional Check
        notional_value = price * quantity
        if notional_value < self.min_trade_amount:
            log(f"⚠️ Alış İptal: İşlem tutarı ({notional_value:.2f}) min limitin ({self.min_trade_amount}) altında.")
            return False

        if self.is_live:
            try:
                # Gerçek işlem
                if self.is_tr:
                    # Precision Adjustment (FLOOR)
                    qty_to_send = quantity
                    info = await self.get_symbol_info(symbol)
                    if info:
                        step_size = float(info.get('stepSize', '1.0'))
                        if step_size > 0:
                            # Adım sayısını hesapla (Aşağı yuvarla)
                            steps = int(quantity / step_size)
                            qty_to_send = steps * step_size
                            
                            # Hassasiyeti ayarla
                            precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
                            if precision > 0:
                                qty_to_send = float("{:.{p}f}".format(qty_to_send, p=precision))
                            else:
                                qty_to_send = int(qty_to_send)
                        else:
                            qty_to_send = int(quantity)

                    # Re-check notional with adjusted quantity
                    if (qty_to_send * price) < self.min_trade_amount:
                         log(f"⚠️ Alış İptal: Hassasiyet sonrası tutar ({qty_to_send * price:.2f}) yetersiz.")
                         return False

                    order = await asyncio.to_thread(
                        self.exchange_spot.new_order,
                        symbol=symbol,
                        side='BUY',
                        type='MARKET',
                        quantity=qty_to_send
                    )
                    
                    # Hata Kontrolü
                    if isinstance(order, dict):
                        if 'code' in order and order['code'] != 0:
                            log(f"❌ Canlı ALIŞ Başarısız: {order.get('msg')} (Code: {order.get('code')})")
                            return False
                        # Check for wrapped data
                        if 'data' in order and isinstance(order['data'], dict):
                             order = order['data']
                    
                    log(f"✅ Canlı ALIŞ Başarılı: {order}")
                else:
                    # Global (CCXT)
                    # Precision Adjustment
                    qty_to_send = quantity
                    info = await self.get_symbol_info(symbol)
                    if info:
                        step_size = float(info.get('stepSize', '1.0'))
                        if step_size > 0:
                            steps = int(quantity / step_size)
                            qty_to_send = steps * step_size
                            precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
                            if precision > 0:
                                qty_to_send = float("{:.{p}f}".format(qty_to_send, p=precision))
                            else:
                                qty_to_send = int(qty_to_send)
                        else:
                            qty_to_send = int(quantity)

                    log(f"🛒 Global Alış Emri: {symbol} - Miktar: {qty_to_send}")
                    order = await asyncio.to_thread(
                        self.exchange_spot.create_market_buy_order,
                        symbol,
                        qty_to_send
                    )
                    log(f"✅ Global ALIŞ Başarılı: {order.get('id')}")

            except Exception as e:
                log(f"❌ Canlı ALIŞ Hatası: {e}")
                return False
        
        # ATR Trailing Stop Başlangıç Değeri
        initial_stop_loss = 0.0
        atr_value = 0.0
        
        if features:
            # VWAP Log
            if 'vwap' in features:
                vwap_val = float(features['vwap'])
                if vwap_val > 0:
                    diff_pct = ((price - vwap_val) / vwap_val) * 100
                    log(f"📊 VWAP Analizi: Fiyat {price} vs VWAP {vwap_val:.4f} (Fark: %{diff_pct:.2f})")

            if 'ATR' in features:
                atr_value = float(features['ATR'])
                # ATR Multiplier: 3.0 (SuperTrend standardı)
                initial_stop_loss = price - (atr_value * 3.0)
                log(f"🛑 ATR Stop-Loss Ayarlandı: {initial_stop_loss:.4f} (ATR: {atr_value:.4f})")

        # Kağıt işlem / Takip
        cost = price * quantity
        if not self.is_live:
             if self.paper_balance >= cost:
                 self.paper_balance -= cost
                 log(f"🧪 Sanal Bakiye Güncellendi: {self.paper_balance:.2f} (-{cost:.2f})")
             else:
                 log(f"⚠️ Sanal Bakiye Yetersiz: {self.paper_balance:.2f} < {cost:.2f}")
                 return False

        self.paper_positions[symbol] = {
            'entry_price': price,
            'quantity': quantity,
            'timestamp': time.time(),
            'highest_price': price,  # Trailing stop için
            'stop_loss': initial_stop_loss, # ATR bazlı dinamik stop
            'atr_value': atr_value,
            'features': features or {} # Öğrenme için özellikleri sakla
        }
        
        # Sipariş Geçmişine Ekle
        order_record = {
            'timestamp': time.time(),
            'symbol': symbol,
            'action': 'BUY',
            'price': price,
            'quantity': quantity,
            'status': 'FILLED',
            'details': features or {}
        }
        self.order_history.append(order_record)
        # Keep last 100 orders
        if len(self.order_history) > 100:
            self.order_history = self.order_history[-100:]

        self.save_positions()
        log(f"📝 Pozisyon açıldı: {symbol} @ {price}")
        return True

    async def execute_sell(self, symbol: str, quantity: float, price: float, position: dict) -> bool:
        """Satış emri"""
        log(f"🔴 SATIŞ Sinyali: {symbol} - Fiyat: {price}")
        
        # Min Notional Check
        notional_value = price * quantity
        min_limit = self.min_trade_amount
        
        # Satışta limitin yarısına kadar tolerans göster (eski pozisyonlar için)
        # Ancak Global/Futures için katı limit (5$) gerekebilir.
        if not self.is_tr:
             min_limit = 5.0 # Global Futures strict limit
        else:
             min_limit = 20.0 # TR için 20 TL (Alış 40 olsa da satış 20 kalsın)

        if notional_value < min_limit:
            log(f"⚠️ Satış İptal: İşlem tutarı ({notional_value:.2f}) min limitin ({min_limit}) altında.")
            # DUST (Toz) Uyarısı
            log(f"⏳ DUST (Toz) Koruması: {symbol} pozisyonu satılamıyor ({notional_value:.2f} < {min_limit}). Değer artana kadar hafızada tutuluyor.")
            return False

        if self.is_live:
            try:
                if self.is_tr:
                    # Precision Adjustment (FLOOR)
                    qty_to_send = quantity
                    info = await self.get_symbol_info(symbol)
                    if info:
                        step_size = float(info.get('stepSize', '1.0'))
                        if step_size > 0:
                            # Adım sayısını hesapla (Aşağı yuvarla)
                            steps = int(quantity / step_size)
                            qty_to_send = steps * step_size
                            
                            # Hassasiyeti ayarla
                            precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
                            if precision > 0:
                                qty_to_send = float("{:.{p}f}".format(qty_to_send, p=precision))
                            else:
                                qty_to_send = int(qty_to_send)
                        else:
                            qty_to_send = int(quantity)

                    # Re-check notional with adjusted quantity
                    if (qty_to_send * price) < 20.0:
                         log(f"⚠️ Satış İptal: Hassasiyet sonrası tutar ({qty_to_send * price:.2f} TRY) yetersiz.")
                         # DUST (Toz) Uyarısı (Hassasiyet Sonrası)
                         log(f"⏳ DUST Uyarısı: {symbol} pozisyonu ({qty_to_send * price:.2f} TRY) hassasiyet sonrası limit altında.")
                         return False

                    order = await asyncio.to_thread(
                        self.exchange_spot.new_order,
                        symbol=symbol,
                        side='SELL',
                        type='MARKET',
                        quantity=qty_to_send
                    )
                    
                    # Hata Kontrolü
                    if isinstance(order, dict):
                        if 'code' in order and order['code'] != 0:
                            code = order.get('code')
                            msg = order.get('msg')
                            log(f"❌ Canlı SATIŞ Başarısız: {msg} (Code: {code})")

                            # Otomatik Düzeltme: Bakiye hatası varsa pozisyonu sil
                            if code == 2202 or code == -2010 or 'Insufficient balance' in str(msg):
                                log(f"⚠️ Kritik Bakiye Hatası: {symbol} cüzdanda yok ama pozisyonda görünüyor. Bot hafızasından siliniyor...")
                                if symbol in self.paper_positions:
                                    del self.paper_positions[symbol]
                                    self.save_positions()

                            return False
                        # Check for wrapped data
                        if 'data' in order and isinstance(order['data'], dict):
                            order = order['data']

                    log(f"✅ Canlı SATIŞ Başarılı: {order}")
                else:
                    # Global (CCXT)
                    qty_to_send = quantity
                    info = await self.get_symbol_info(symbol)
                    if info:
                        step_size = float(info.get('stepSize', '1.0'))
                        if step_size > 0:
                            steps = int(quantity / step_size)
                            qty_to_send = steps * step_size
                            precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
                            if precision > 0:
                                qty_to_send = float("{:.{p}f}".format(qty_to_send, p=precision))
                            else:
                                qty_to_send = int(qty_to_send)
                        else:
                            qty_to_send = int(quantity)

                    params = {}
                    if settings.TRADING_MODE == 'futures':
                         params['reduceOnly'] = True
                    
                    log(f"💰 Global Satış Emri: {symbol} - Miktar: {qty_to_send}")
                    order = await asyncio.to_thread(
                        self.exchange_spot.create_market_sell_order,
                        symbol,
                        qty_to_send,
                        params
                    )
                    
                    # CCXT returns dict directly usually
                    order_id = order.get('id') if isinstance(order, dict) else str(order)
                    log(f"✅ Global SATIŞ Başarılı: {order_id}")

            except Exception as e:
                log(f"❌ Canlı SATIŞ Hatası: {e}")
                return False

        # PnL Hesapla
        entry_price = position['entry_price']
        pnl_pct = ((price - entry_price) / entry_price) * 100
        
        # BRAIN LEARNING (Sonucu kaydet ve ağırlıkları güncelle)
        if hasattr(self, 'brain'):
            features = position.get('features', {})
            # Özellik yoksa (eski pozisyonlar için) öğrenme yapma
            if features:
                learn_msg = self.brain.record_outcome(symbol, pnl_pct, features, entry_price, price)
                log(f"🧠 {learn_msg}")
        
        # İstatistikleri güncelle
        self.initialize_daily_stats()
        self.stats['daily_realized_pnl'] += pnl_pct  # Basit toplama (yüzdesel)
        self.stats['daily_trade_count'] += 1
        self.stats['total_pnl_pct'] += pnl_pct
        self.stats['total_trades'] += 1
        if pnl_pct > 0:
            wins = (self.stats.get('win_rate', 0) * (self.stats['total_trades'] - 1)) + 1
            self.stats['win_rate'] = wins / self.stats['total_trades']
        else:
            wins = (self.stats.get('win_rate', 0) * (self.stats['total_trades'] - 1))
            self.stats['win_rate'] = wins / self.stats['total_trades']
            
        # Pozisyonu sil
        if symbol in self.paper_positions:
            del self.paper_positions[symbol]
            
        if not self.is_live:
            revenue = price * quantity
            self.paper_balance += revenue
            log(f"🧪 Sanal Bakiye Güncellendi: {self.paper_balance:.2f} (+{revenue:.2f})")

        # Sipariş Geçmişine Ekle
        order_record = {
            'timestamp': time.time(),
            'symbol': symbol,
            'action': 'SELL',
            'price': price,
            'quantity': quantity,
            'pnl_pct': pnl_pct,
            'status': 'FILLED'
        }
        self.order_history.append(order_record)
        if len(self.order_history) > 100:
            self.order_history = self.order_history[-100:]

        self.save_positions()
        self.state_manager.save_stats(self.stats)
        
        log(f"📝 Pozisyon kapatıldı: {symbol} @ {price} | PnL: %{pnl_pct:.2f}")
        return True

    def check_risk_conditions(self, symbol: str, current_price: float, df: pd.DataFrame = None) -> dict:
        """
        StopLossManager üzerinden risk kontrollerini yapar.
        Dönüş: {'action': 'CLOSE'|'PARTIAL_CLOSE'|'HOLD', 'reason': str, ...}
        """
        if symbol not in self.paper_positions:
            return {'action': 'HOLD'}
            
        position = self.paper_positions[symbol]
        current_time = datetime.now()
        
        # StopLossManager kontrolü
        result = self.stop_loss_manager.check_exit_conditions(position, current_price, current_time, df)
        
        # Eğer stop fiyatı güncellendiyse kaydet
        if 'new_stop_price' in result:
            position['stop_loss'] = result['new_stop_price']
            # log(f"🛡️ Stop Loss Güncellendi ({symbol}): {result['new_stop_price']:.4f}")
            self.save_positions()
            
        return result

    def update_atr_trailing_stop(self, symbol: str, current_price: float, current_atr: float) -> bool:
        """
        LEGACY: Artık check_risk_conditions kullanılıyor, ancak geriye dönük uyumluluk için bırakıldı.
        """
        return False


    async def place_limit_order(self, symbol: str, side: str, price: float, quantity: float) -> Optional[Dict]:
        """Limit emir gönder (Grid Trading için)"""
        # Hassasiyet ayarı
        try:
            # Sembol bilgilerini al (Precision için)
            step_size = 1.0
            tick_size = 0.01
            min_qty = 0.0
            
            if self.is_live and self.exchange_spot:
                info = await self.get_symbol_info(symbol)
                if info:
                    step_size = float(info.get('stepSize', '1.0'))
                    tick_size = float(info.get('tickSize', '0.01'))
                    min_qty = float(info.get('minQty', '0.0'))

            # Fiyat hassasiyeti (tickSize)
            if tick_size > 0:
                price_precision = int(round(-math.log10(tick_size)))
                price = round(price, price_precision)
                price_str = "{:.{p}f}".format(price, p=price_precision)
            else:
                price_str = "{:.2f}".format(price)

            # Miktar hassasiyeti (stepSize)
            if step_size > 0:
                qty_precision = int(round(-math.log10(step_size)))
                quantity = round(quantity, qty_precision)
                qty_str = "{:.{p}f}".format(quantity, p=qty_precision)
            else:
                quantity = int(quantity)
                qty_str = str(quantity)

            # Min miktar kontrolü
            if quantity < min_qty:
                log(f"⚠️ Limit Emir İptal: Miktar ({quantity}) min limitin ({min_qty}) altında.")
                return None
             
            log(f"🧱 LIMIT EMİR: {side} {symbol} @ {price_str} x {qty_str}")
             
            if self.is_live and self.exchange_spot:
                if self.is_tr:
                    # Binance TR
                    order = await asyncio.to_thread(
                        self.exchange_spot.new_order,
                        symbol=symbol,
                        side=side,
                        type='LIMIT',
                        quantity=float(qty_str),
                        price=float(price_str),
                        params={'timeInForce': 'GTC'}
                    )
                    
                    # Binance TR response normalization
                    if order and isinstance(order, dict):
                        if 'data' in order and isinstance(order['data'], dict):
                            order = order['data']
                        elif 'code' in order and order['code'] != 0:
                            log(f"❌ Limit Emir Başarısız: {order.get('msg')} (Code: {order.get('code')})")
                            return None

                    if not order or 'orderId' not in order:
                        log(f"❌ Limit Emir Yanıtı Beklenmedik: {order}")
                        return None

                    log(f"✅ Limit Emir Başarılı: {order.get('orderId')}")
                    return order
                else:
                    # Global (Mock/CCXT)
                    pass
            
            # Paper Trading simülasyonu
            mock_order_id = int(time.time() * 1000)
            log(f"📝 [PAPER] Limit Emir Kaydedildi: ID {mock_order_id}")
            
            # Paper emirlerini hafızada tutabiliriz (gerçekleşme simülasyonu için)
            # Şimdilik sadece ID dönüyoruz
            return {
                'orderId': mock_order_id,
                'symbol': symbol,
                'price': price,
                'origQty': quantity,
                'side': side,
                'status': 'NEW'
            }
             
        except Exception as e:
            log(f"❌ Limit Emir Hatası: {e}")
            return None

    async def check_daily_loss_limit(self) -> bool:
        """Günlük zarar limitini kontrol et"""
        if self.stats.get('daily_realized_pnl', 0.0) <= -self.max_daily_loss:
             log(f"🛑 Günlük zarar limiti aşıldı: %{self.stats['daily_realized_pnl']:.2f}")
             return True
        return False

    async def close(self):
        """Kaynakları temizle"""
        log("Executor kapatılıyor...")
        self.state_manager.save_state(self.paper_positions)
        self.state_manager.save_stats(self.stats)
        if self.is_tr and self.exchange_spot:
             self.exchange_spot.close()

    def stop(self):
        """Executor'ı durdur"""
        log("Executor durduruluyor...")
        self.save_positions()
        self.state_manager.save_stats(self.stats)
