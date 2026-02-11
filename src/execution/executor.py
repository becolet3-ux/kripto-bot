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
from src.utils.exceptions import BotError, InsufficientBalanceError, ExchangeError
from src.learning.brain import BotBrain
from src.strategies.analyzer import TradeSignal
from src.execution.stop_loss_manager import StopLossManager
from src.risk.position_sizer import PositionSizer
from config.settings import settings

class BinanceExecutor:
    def __init__(self, exchange_client=None, is_tr=False):
        self.exchange_spot = exchange_client
        self.is_tr = is_tr
        self.is_live = settings.LIVE_TRADING
        self.state_manager = StateManager(filepath=settings.STATE_FILE, stats_filepath=settings.STATS_FILE)
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
        
        # Initialize commentary if missing
        if 'commentary' not in self.full_state:
            self.full_state['commentary'] = {
                "market_regime": {"trend": "ANALYZING", "volatility": "LOW"},
                "active_strategy": "Başlatılıyor...",
                "top_opportunities": [],
                "portfolio_analysis": {},
                "last_updated": time.time(),
                "brain_plan": None,
                "brain_plan_history": []
            }
        
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
        self.position_sizer = PositionSizer()
        
        # Min Trade Amount Configuration
        # Global / USDT Mode
        if self.is_tr:
             self.min_trade_amount = 40.0 # TRY
        else:
             # Increase to 10.0 to prevent NOTIONAL filter failures (Code -1013)
             # Binance often enforces 10 USDT min notional for API orders
             # UPDATE: Lowered to 5.5 to allow trading with small balances (User has ~6 USD)
             self.min_trade_amount = 5.5 # USDT
            
        log(f"Executor başlatıldı. Mod: {'CANLI' if self.is_live else 'KAĞIT'} | Min İşlem: {self.min_trade_amount} {'TRY' if self.is_tr else 'USDT'}")
        
        # Initial state save to ensure mode is correctly recorded
        self.save_positions()

    def save_positions(self):
        """Pozisyonları state dosyasına kaydet"""
        self.full_state['paper_positions'] = self.paper_positions
        self.full_state['order_history'] = self.order_history
        self.full_state['is_live'] = self.is_live
        self.full_state['paper_balance'] = self.paper_balance
        
        # Save MTF Stats if available
        if hasattr(self, 'mtf_stats'):
            self.full_state['mtf_stats'] = self.mtf_stats
        
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

    def update_mtf_stats(self, stats: Dict):
        """Update Multi-Timeframe Stats"""
        self.mtf_stats = stats
        self.full_state['mtf_stats'] = stats
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
             await self.sync_wallet()



    async def redeem_flexible_savings(self):
        """
        Redeems all assets from Binance Flexible Earn (Simple Earn) to Spot Wallet.
        This allows the bot to access funds hidden in 'Earn' wallets.
        """
        try:
            # Check if API method exists (SAPI support)
            if not hasattr(self.exchange_spot, 'sapi_get_simple_earn_flexible_position'):
                return

            # log("🏦 Checking Flexible Earn positions to redeem...")
            
            # 1. Get Positions
            # GET /sapi/v1/simple-earn/flexible/position
            positions = await asyncio.to_thread(
                self.exchange_spot.sapi_get_simple_earn_flexible_position,
                {'size': 100}
            )
            
            rows = positions.get('rows', []) if isinstance(positions, dict) else positions
            
            if not rows:
                return

            redeemed_count = 0
            for pos in rows:
                asset = pos.get('asset')
                amount = float(pos.get('totalAmount', 0.0))
                product_id = pos.get('productId')
                
                # Filter small amounts (dust in earn)? No, redeem everything to clean up.
                if amount <= 0: continue
                
                log(f"🏦 Redeeming {asset} (Amount: {amount}) from Earn to Spot...")
                
                try:
                    # POST /sapi/v1/simple-earn/flexible/redeem
                    # API Error -1102 said 'amount' was missing, so we use 'amount' instead of 'redeemAmount'
                    await asyncio.to_thread(
                        self.exchange_spot.sapi_post_simple_earn_flexible_redeem,
                        {
                            'productId': product_id,
                            'amount': amount, 
                            'destAccount': 'SPOT' 
                        }
                    )
                    redeemed_count += 1
                    log(f"✅ Successfully redeemed {asset}.")
                except Exception as e:
                    log(f"❌ Failed to redeem {asset}: {e}")
            
            if redeemed_count > 0:
                log(f"🏦 Redeemed {redeemed_count} assets from Earn. Waiting for balance update...")
                await asyncio.sleep(2) # Wait for transfer to process
                
        except Exception as e:
            # Use debug log for errors to avoid spamming if user has no Earn access
            # log(f"DEBUG: Earn Redemption Error: {e}")
            pass

    async def transfer_funding_to_spot(self):
        """
        Transfers all assets from Funding Wallet to Spot Wallet.
        """
        try:
            # 1. Get Funding Balance
            funding_balance = await asyncio.to_thread(self.exchange_spot.fetch_balance, {'type': 'funding'})
            total = funding_balance.get('total', {})
            
            transferred_count = 0
            for asset, amount in total.items():
                if amount > 0:
                    log(f"💰 Found {asset} ({amount}) in Funding Wallet. Transferring to Spot...")
                    try:
                        # POST /sapi/v1/asset/transfer
                        # type: FUNDING_MAIN
                        await asyncio.to_thread(
                            self.exchange_spot.sapi_post_asset_transfer,
                            {
                                'type': 'FUNDING_MAIN',
                                'asset': asset,
                                'amount': amount
                            }
                        )
                        transferred_count += 1
                        log(f"✅ Transferred {asset} to Spot.")
                    except Exception as e:
                        log(f"❌ Failed to transfer {asset}: {e}")
            
            if transferred_count > 0:
                await asyncio.sleep(1)
            else:
                log("💰 Funding Wallet check complete. No assets to transfer.")

        except Exception as e:
            log(f"⚠️ Funding check failed: {e}")
            pass

    async def convert_dust_to_bnb(self):
        """
        Binance Global: Convert small balances (dust) to BNB.
        Scans for assets < 10 USDT and converts them.
        """
        if self.is_tr:
            log("⚠️ Binance TR does not support Dust-to-BNB conversion via API.")
            return

        try:
            log("🧹 Scanning for dust assets to convert to BNB...")
            
            # 1. Get Balances
            balance_data = await asyncio.to_thread(self.exchange_spot.fetch_balance)
            balances = balance_data.get('total', {})
            
            # 2. Get Tickers for Valuation
            tickers = await asyncio.to_thread(self.exchange_spot.fetch_tickers)
            
            dust_candidates = []
            
            for asset, amount in balances.items():
                if asset in ['USDT', 'BNB', 'TRY', 'USDC', 'FDUSD']: continue # Skip bases
                if amount <= 0: continue
                
                # Symbol check
                symbol = f"{asset}/USDT"
                price = 0.0
                
                if symbol in tickers:
                    price = float(tickers[symbol]['last'])
                else:
                    # Maybe it has no USDT pair (e.g. BTC pair only)
                    # Skip for safety or check BTC value
                    # log(f"⚠️ Dust Check: No USDT pair for {asset}")
                    continue
                    
                value_usdt = amount * price
                log(f"🔍 Dust Check: {asset} Amount: {amount} Value: ${value_usdt:.2f}")
                
                # Criteria: Value < 10 USDT (Min Trade) and > 0.1 USDT (To avoid zero value)
                if 0.1 < value_usdt < 10.0:
                    dust_candidates.append(asset)
                    log(f"🧹 Dust Candidate Found: {asset} (${value_usdt:.2f})")
            
            if not dust_candidates:
                log("🧹 No dust assets found to convert.")
                return

            log(f"🧹 Found {len(dust_candidates)} dust assets: {dust_candidates}")
            
            # 3. Call API
            # Binance API expects 'asset': ['BTC', 'ETH']
            response = await asyncio.to_thread(
                self.exchange_spot.sapi_post_asset_dust,
                {'asset': dust_candidates}
            )
            
            log(f"✅ Dust-to-BNB Conversion Result: {response}")
            
        except Exception as e:
            log(f"❌ Dust conversion failed: {e}")

    async def _import_wallet_to_positions(self, wallet_assets: dict):
        """
        Cüzdandaki varlıkları (bot tarafından alınmamış olsa bile) pozisyonlara ekler.
        Ayrıca cüzdanda olmayan (satılmış/sıfırlanmış) varlıkları bot hafızasından siler.
        """
        try:
            # 1. Cleanup: Cüzdanda artık olmayan varlıkları hafızadan sil
            to_remove = []
            for symbol in list(self.paper_positions.keys()):
                # Sembol isminden varlık kodunu çıkar
                asset = None
                if self.is_tr:
                    if symbol.endswith('_TRY'):
                        asset = symbol.replace('_TRY', '')
                else:
                    # Global: 'BAT/USDT' -> 'BAT'
                    if '/' in symbol:
                        asset = symbol.split('/')[0]
                
                if asset:
                    # Eğer varlık cüzdan listesinde yoksa (bakiye 0 ise wallet_assets'e girmez)
                    # VEYA cüzdan listesinde var ama toplam bakiye çok düşükse (dust)
                    if asset not in wallet_assets:
                        to_remove.append(symbol)
                    elif wallet_assets[asset]['total'] <= 0: # Should be covered by 'not in' but safe check
                        to_remove.append(symbol)
            
            for sym in to_remove:
                del self.paper_positions[sym]
                log(f"🧹 Cüzdandan silinen varlık bot hafızasından kaldırıldı: {sym}")

            # 2. Import: Cüzdanda olup botta olmayanları ekle
            for asset, data in wallet_assets.items():
                if asset == 'TRY': continue
                if not self.is_tr and asset == 'USDT': continue # Global için USDT ana para
                
                # Sembol ismini oluştur
                symbol = ""
                if self.is_tr:
                    symbol = f"{asset}_TRY"
                else:
                    symbol = f"{asset}/USDT"
                
                # Bu varlık zaten pozisyonlarımızda var mı?
                if symbol in self.paper_positions:
                    # Mevcut miktarı güncelle (Senkronizasyon)
                    current_qty = self.paper_positions[symbol].get('quantity', 0.0)
                    wallet_qty = float(data.get('total', 0.0))
                    
                    # Eğer fark %1'den büyükse güncelle
                    if abs(current_qty - wallet_qty) > (wallet_qty * 0.01) and wallet_qty > 0:
                        old_qty = self.paper_positions[symbol]['quantity']
                        self.paper_positions[symbol]['quantity'] = wallet_qty
                        
                        # Tahmini değer hesapla (Log anlaşılsın diye)
                        est_value = wallet_qty * self.paper_positions[symbol].get('entry_price', 0.0)
                        log(f"🔄 Bakiye Senkronize Edildi ({symbol}): {old_qty:.4f} -> {wallet_qty:.4f} Adet (~${est_value:.2f})")
                    continue
                
                # Bu varlık işlem yaptığımız semboller listesinde mi?
                # Eğer listede yoksa bile cüzdanda varsa eklemeliyiz ki satabilelim (Sniper Mode için)
                # Ancak fiyatını bulmamız lazım.
                
                free_amount = float(data.get('free', 0.0)) + float(data.get('locked', 0.0))
                if free_amount <= 0: continue

                # Güncel fiyatı al (Değer kontrolü ve entry_price için)
                current_price = 0.0
                try:
                    # Mevcut ticker varsa kullan, yoksa fetch
                    # Ticker fetch maliyetli olabilir, bu yüzden sadece gerektiğinde
                    ticker = await asyncio.to_thread(self.exchange_spot.fetch_ticker, symbol)
                    current_price = float(ticker['last'])
                except:
                    # Ticker bulunamadıysa (örn delist olmuş veya yanlış pair), geç
                    continue 

                if current_price <= 0: continue

                # Minimum değer kontrolü (Global için min_trade_amount, TR için 10 TRY)
                total_value = free_amount * current_price
                threshold = 10.0 if self.is_tr else 1.0 # 1$ altı dust sayılabilir ama satılabilirse alalım
                
                if total_value < threshold:
                    continue

                # Pozisyonu ekle
                log(f"🎒 Cüzdanda mevcut varlık tespit edildi: {symbol} ({free_amount} adet, ~{total_value:.2f} {('TRY' if self.is_tr else 'USDT')}). Bota dahil ediliyor.")
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

    async def sync_wallet(self):
        """Gerçek cüzdan bakiyelerini state'e senkronize et (Auto-Redeem dahil)"""
        if not self.is_live or not self.exchange_spot:
            # log(f"DEBUG: Skipping wallet sync. Live: {self.is_live}, Client: {self.exchange_spot}")
            return

        try:
            # --- Auto-Redeem from Earn (Flexible Savings) if Global ---
            # This ensures hidden assets (like AVAX in Earn) are moved to Spot for trading
            if not self.is_tr:
                await self.redeem_flexible_savings()
                await self.transfer_funding_to_spot()

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
            # log(f"💰 Cüzdan Senkronize: {len(wallet_assets)} varlık bulundu. Varlıklar: {list(wallet_assets.keys())}. Bakiye: {total_try_balance:.2f}")

        except Exception as e:
            log(f"⚠️ Cüzdan senkronizasyon hatası: {e}")

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
                usdt_total = float(balance.get('total', {}).get('USDT', 0.0))
                
                # Add value of other assets in paper_positions
                # Since sync_wallet should populate paper_positions, we can trust it roughly
                # Or we can iterate balance['total'] again?
                # Using paper_positions is faster and uses cached prices
                
                other_assets_value = 0.0
                for sym, pos in self.paper_positions.items():
                    # Calculate value (qty * price)
                    # We use entry_price or highest_price as estimate if current price unknown
                    # Ideally we have current price from main loop but executor doesn't have it easily here
                    est_price = pos.get('entry_price', 0.0)
                    qty = pos.get('quantity', 0.0)
                    other_assets_value += qty * est_price
                
                return usdt_total + other_assets_value

        except Exception as e:
            log(f"⚠️ Bakiye hesaplama hatası: {e}")
            return 0.0

    async def calculate_quantity(self, symbol: str, price: float, side: str, risk_score: float = 10.0, atr_value: float = 0.0, regime: str = 'NEUTRAL', force_all_in: bool = False) -> float:
        """
        İşlem miktarını hesapla (Dinamik Risk Yönetimi + Volatilite Bazlı + Market Rejimi - Phase 3)
        force_all_in: Eğer True ise, bakiyenin tamamı (%98'i) ile işlem açılır (Sniper Mode).
        """
        try:
            total_balance = await self.get_total_balance()
            
            # Base Asset (USDT/TRY) Free Balance
            base_asset = 'TRY' if self.is_tr else 'USDT'
            free_balance = await self.get_free_balance(base_asset)

            if total_balance <= 0:
                return 0.0
                
            # --- SNIPER MODE (ALL-IN) ---
            if force_all_in:
                # Tüm bakiyeyi kullan (Komisyon payı için %2 bırak)
                current_leverage = settings.LEVERAGE if (not self.is_tr and settings.TRADING_MODE == 'futures') else 1.0
                
                # Futures ise Kaldıraç Ayarla
                if self.is_live and not self.is_tr and settings.TRADING_MODE == 'futures':
                    try:
                        log(f"⚙️ Sniper Modu: Kaldıraç Ayarlanıyor ({symbol}): {current_leverage}x")
                        await asyncio.to_thread(self.exchange_spot.set_leverage, current_leverage, symbol)
                    except Exception as e:
                        log(f"⚠️ Kaldıraç ayarlama hatası: {e}")
                
                # FIX: Use FREE balance for All-In, not Total Equity
                # This prevents "Insufficient Balance" errors if equity is locked in other positions/dust
                risk_pct = settings.SNIPER_MAX_RISK_PCT / 100.0
                target_position_size_usdt = free_balance * current_leverage * risk_pct
                
                log(f"🎯 SNIPER MODU: Tüm serbest bakiye kullanılıyor! Hedef Notional={target_position_size_usdt:.2f} (Free={free_balance:.2f}, Risk=%{risk_pct*100})")
                
                # Miktar hesapla ve dön
                quantity = target_position_size_usdt / price
                return quantity

            # Phase 2 & 3: Volatility & Regime Based Position Sizing
            # Use Total Equity (total_balance) for risk calculations
            balance = total_balance 
            
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
                
                log(f"⚖️ Pozisyon Hesaplama (Phase 2): Bakiye={balance:.2f} (Free: {free_balance:.2f}) | Risk={params['risk_level']} | Kaldıraç={target_leverage}x | Hedef Notional={target_position_size_usdt:.2f}")

            else:
                # Fallback: Eski Mantık (ATR yoksa)
                base_pct = settings.MAX_POSITION_PCT / 100.0
                confidence_factor = max(0.2, min(1.0, risk_score / 10.0))
                target_position_size_usdt = balance * base_pct * confidence_factor # Bu notional mı margin mi? Eski kodda margin gibi kullanılıyordu (Lev=1 varsayımı ile)
                if not self.is_tr and settings.TRADING_MODE == 'futures':
                     # Eğer futures ise ve ATR yoksa varsayılan kaldıraçla notional hesapla
                     target_position_size_usdt *= settings.LEVERAGE 
                
                log(f"⚖️ Pozisyon Hesaplama (Fallback): Bakiye={balance:.2f} (Free: {free_balance:.2f}) | Baz=%{base_pct*100} | Hedef={target_position_size_usdt:.2f}")

            
            # Minimum İşlem Tutarı Kontrolü
            min_trade_val = self.min_trade_amount
            
            # Eğer hesaplanan tutar min limitin altındaysa ve bakiye yetiyorsa yükselt
            if target_position_size_usdt < min_trade_val:
                # Bakiyemiz min tutarı karşılıyor mu? (Komisyon payı ile)
                # Not: Futures için margin kontrolü gerekir. Margin = Notional / Leverage
                required_margin = min_trade_val / (target_leverage if 'target_leverage' in locals() else settings.LEVERAGE)
                
                # FIX: Check FREE BALANCE (not Total Equity) to ensure we can actually open this trade
                # If free balance is low, do NOT bump up the size.
                if free_balance >= (required_margin * 1.05): 
                    target_position_size_usdt = min_trade_val * 1.05
            
            # Güvenlik: Asla toplam bakiyeden (kaldıraçlı) fazla işlem açma
            # Max Notional = Balance * Leverage * RiskPct
            current_leverage = target_leverage if 'target_leverage' in locals() else settings.LEVERAGE
            risk_pct = settings.SNIPER_MAX_RISK_PCT / 100.0
            
            max_safe_notional_equity = balance * current_leverage * risk_pct
            
            # Phase 3 FIX: Ayrıca mevcut kullanılabilir bakiyeyi de kontrol et (Total Equity'e güvenme)
            # Free Balance * Leverage * RiskPct
            max_safe_notional_free = free_balance * current_leverage * risk_pct
            
            # En kısıtlayıcı olanı seç
            max_safe_notional = min(max_safe_notional_equity, max_safe_notional_free)
            
            if target_position_size_usdt > max_safe_notional:
                log(f"📉 Bakiye Koruması: Tutar {target_position_size_usdt:.2f} -> {max_safe_notional:.2f} olarak sınırlandı (Free: {free_balance:.2f})")
                target_position_size_usdt = max_safe_notional
            
            # Son kontrol
            if target_position_size_usdt < min_trade_val:
                log(f"⚠️ Yetersiz Bakiye: {target_position_size_usdt:.2f} < {min_trade_val}. İşlem iptal.")
                raise InsufficientBalanceError(f"Insufficient funds for minimum trade: {target_position_size_usdt:.2f} < {min_trade_val}")
            
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
                            min_notional_filter = filters.get('MIN_NOTIONAL', {})
                            if not min_notional_filter:
                                min_notional_filter = filters.get('NOTIONAL', {})
                                
                            return {
                                'stepSize': lot_size.get('stepSize', '1.0'),
                                'minQty': lot_size.get('minQty', '0.0'),
                                'tickSize': price_filter.get('tickSize', '0.01'),
                                'minNotional': min_notional_filter.get('minNotional', '10.0')
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
                            'tickSize': str(market['precision'].get('price', 0.01)),
                            'minNotional': str(market['limits']['cost'].get('min', 5.0))
                        }
            return None
        except Exception as e:
            log(f"Sembol bilgi hatası: {e}")
            return None

    async def execute_strategy(self, signals: Union[pd.DataFrame, TradeSignal, List[TradeSignal]], latest_scores: Dict[str, float] = None):
        """Sinyalleri işle"""
        # Günlük zarar limiti kontrolü (realized PnL yüzdesi üzerinden, legacy güvenlik katmanı)
        # Not: daily_realized_pnl, her işlemde yüzdesel PnL toplamı olarak tutuluyor.
        daily_realized_pct = self.stats.get('daily_realized_pnl', 0.0)
        if daily_realized_pct <= -self.max_daily_loss:
            if not self.emergency_stop:
                log(f"🛑 GÜNLÜK ZARAR LİMİTİ AŞILDI (Realized) (%{self.max_daily_loss}). İşlemler durduruluyor.")
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
                    
                    # Force All-In (Sniper Mode)
                    force_all_in = sig.details.get('force_all_in', False) if sig.details else False
                    
                    if force_all_in:
                        qty = await self.calculate_quantity(symbol, price, 'BUY', risk_score=score, atr_value=sig.details.get('atr', 0), force_all_in=True)
                        if qty > 0:
                             log(f"🎯 Sniper Girişi: {symbol} için Tüm Bakiye Kullanılıyor.")
                             await self.execute_buy(symbol, qty, price)
                        return # Diğer kontrolleri atla

                    # --- SMART SWAP LOGIC (DISABLED) ---
                    # Yetersiz bakiye durumunda swap işlemleri artık main.py içinde
                    # OpportunityManager ve 3-Loop Confirmation ile yönetiliyor.
                    # Bu blok, teyitsiz işlem yapmaması için devre dışı bırakıldı.
                    
                    # Normal Mode: Proceed to calculate quantity based on balance
                    pass 
                    
                    # --- SMART SWAP LOGIC END ---
                    
                    # Final Limit Check
                    if len(self.paper_positions) >= settings.MAX_OPEN_POSITIONS:
                        log(f"🛑 Maksimum pozisyon sınırı ({settings.MAX_OPEN_POSITIONS}) dolu. Yeni işlem yapılmıyor.")
                        continue

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
        
        # Phase 3 Improvement: Allow Global/Futures to proceed to "Bump Logic" if value is low but balance is sufficient.
        # Only enforce strict early blocking for TR (strict limits) or Paper Trading (simulation).
        if self.is_tr or not self.is_live:
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

                    # Min Notional Check & Adjustment (Dynamic from Exchange Info)
                    min_notional = 5.0
                    if info:
                         min_notional = float(info.get('minNotional', 5.0))
                    
                    # Log Min Notional Info
                    log(f"ℹ️ {symbol} Min Notional Check: Limit={min_notional} | Order Value={qty_to_send * price:.2f}")

                    if (qty_to_send * price) < min_notional:
                         # BUMP LOGIC WITH SAFETY CHECK
                         base_asset = 'USDT' # Global default
                         # Performance: Cache this or accept slight delay? Safety first.
                         try:
                             check_balance = await self.get_free_balance(base_asset)
                             check_leverage = settings.LEVERAGE if (not self.is_tr and settings.TRADING_MODE == 'futures') else 1.0
                             max_afford_notional = check_balance * check_leverage * 0.98
                             
                             required_bump_notional = min_notional * 1.05
                             
                             if max_afford_notional < required_bump_notional:
                                 log(f"⚠️ Min Notional ({min_notional}) için bakiye yetersiz. (Max: {max_afford_notional:.2f}). İşlem iptal.")
                                 return False
                             
                             log(f"⚠️ Min Notional Altında: {qty_to_send * price:.2f} < {min_notional}. Miktar artırılıyor (+%5)...")
                             qty_to_send = required_bump_notional / price
                             
                         except Exception as e:
                             log(f"⚠️ Balance check error during bump: {e}")
                             # Fallback: Try bumping anyway and let retry logic handle if fails
                             qty_to_send = (min_notional * 1.05) / price

                    if info:
                        step_size = float(info.get('stepSize', '1.0'))
                        if step_size > 0:
                            # 1. Rounding down first (Standard)
                            steps = int(qty_to_send / step_size)
                            qty_to_send = steps * step_size
                            
                            # 2. Check if rounding down caused it to fall below minNotional
                            if (qty_to_send * price) < min_notional:
                                log(f"⚠️ Yuvarlama sonrası Min Notional Altı: {qty_to_send * price:.2f} < {min_notional}. Bir adım yukarı yuvarlanıyor...")
                                steps += 1
                                qty_to_send = steps * step_size

                            # 3. Apply string formatting for precision
                            precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
                            if precision > 0:
                                qty_to_send = float("{:.{p}f}".format(qty_to_send, p=precision))
                            else:
                                qty_to_send = int(qty_to_send)
                        else:
                            qty_to_send = int(qty_to_send)

                    log(f"🛒 Global Alış Emri: {symbol} - Miktar: {qty_to_send}")
                    try:
                        order = await asyncio.to_thread(
                            self.exchange_spot.create_market_buy_order,
                            symbol,
                            qty_to_send
                        )
                        log(f"✅ Global ALIŞ Başarılı: {order.get('id')}")
                    except Exception as e:
                        # RETRY LOGIC FOR INSUFFICIENT BALANCE
                        err_msg = str(e)
                        if 'Insufficient balance' in err_msg or 'Account has insufficient balance' in err_msg or '-2010' in err_msg:
                            log(f"⚠️ Yetersiz Bakiye Hatası alındı. Miktar güncellenip tekrar deneniyor... (Hata: {err_msg[:50]}...)")
                            
                            # 1. Get Fresh Free Balance
                            base_asset = 'USDT' # Global default
                            free_balance = await self.get_free_balance(base_asset)
                            
                            # 2. Calculate Max Safe Quantity (98% of free balance)
                            # Assuming Leverage 1x for retry to be safe, or use current leverage if futures
                            current_leverage = settings.LEVERAGE if (not self.is_tr and settings.TRADING_MODE == 'futures') else 1.0
                            new_notional = free_balance * current_leverage * 0.98
                            
                            # Min Notional Check for Retry
                            min_notional_retry = 5.0
                            if info:
                                min_notional_retry = float(info.get('minNotional', 5.0))

                            if new_notional < min_notional_retry:
                                log(f"❌ Retry İptal: Güncel bakiye ({free_balance:.2f} {base_asset}) min notional ({min_notional_retry}) karşılanamıyor.")
                                return False
                            
                            new_qty = new_notional / price
                            
                            # 3. Re-apply Precision
                            qty_to_send = new_qty
                            if info:
                                step_size = float(info.get('stepSize', '1.0'))
                                if step_size > 0:
                                    steps = int(new_qty / step_size)
                                    qty_to_send = steps * step_size
                                    precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
                                    if precision > 0:
                                        qty_to_send = float("{:.{p}f}".format(qty_to_send, p=precision))
                                    else:
                                        qty_to_send = int(qty_to_send)
                                else:
                                    qty_to_send = int(new_qty)
                            
                            log(f"🛒 Global Alış Emri (RETRY): {symbol} - Yeni Miktar: {qty_to_send}")
                            
                            # 4. Retry Order
                            order = await asyncio.to_thread(
                                self.exchange_spot.create_market_buy_order,
                                symbol,
                                qty_to_send
                            )
                            log(f"✅ Global ALIŞ Başarılı (Retry): {order.get('id')}")
                        else:
                            raise ExchangeError(f"Buy failed after retry check: {e}") from e

            except Exception as e:
                log(f"❌ Canlı ALIŞ Hatası: {e}")
                raise ExchangeError(f"Buy execution failed: {e}") from e
        
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
            'features': features or {}, # Öğrenme için özellikleri sakla
            'is_sniper_mode': features.get('force_all_in', False) if features else False
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

    async def execute_sell(self, symbol: str, quantity: float, price: float, position: dict, is_partial: bool = False) -> bool:
        """Satış emri"""
        
        # Safety: If price is 0, try to fetch it
        if price <= 0.0 and self.exchange_spot:
             try:
                 ticker = await asyncio.to_thread(self.exchange_spot.fetch_ticker, symbol)
                 price = float(ticker['last'])
                 log(f"⚠️ Fiyat 0.0 geldi, güncel fiyat çekildi: {price}")
             except Exception as e:
                 log(f"❌ Fiyat çekme hatası: {e}")

        log(f"🔴 SATIŞ Sinyali: {symbol} - Fiyat: {price}")

        # Live Mode: Check Actual Balance First to prevent 'Insufficient Balance' errors
        if self.is_live:
            try:
                # Parse asset name
                asset = None
                if self.is_tr:
                    if symbol.endswith('_TRY'): asset = symbol.replace('_TRY', '')
                else:
                    if '/' in symbol: asset = symbol.split('/')[0]
                
                if asset:
                    actual_balance = await self.get_free_balance(asset)
                    
                    # Eger elimizdeki miktar, satmak istedigimizden azsa, gercek bakiyeyi kullan
                    if actual_balance < quantity:
                        # Eger fark cok kucukse (rounding) veya buyukse (sync hatasi), yine de gercegi kullanmak zorundayiz
                        # Cunku olmayan parayi satamayiz.
                        if actual_balance > 0:
                            log(f"⚠️ Satış Öncesi Bakiye Düzeltmesi: {asset} Hedef={quantity:.6f} -> Mevcut={actual_balance:.6f}")
                            quantity = actual_balance
                        else:
                             log(f"⚠️ Kritik: {asset} bakiyesi 0 görünüyor! Satış iptal edilebilir.")
                             # Miktari 0 yaparsak asagida min notional'a takilir ve iptal olur, bu dogru davranis.
                             quantity = 0.0

            except Exception as e:
                log(f"⚠️ Satış öncesi bakiye kontrolü hatası: {e}")
        
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
            
        # Pozisyonu sil veya güncelle
        if symbol in self.paper_positions:
            if is_partial:
                # Kısmi satışta miktarı güncelle
                current_qty = self.paper_positions[symbol]['quantity']
                remaining_qty = current_qty - quantity
                
                # Hassasiyet hatalarını önlemek için çok küçük miktarları sıfır kabul et
                if remaining_qty < (self.min_trade_amount / price / 10): 
                    del self.paper_positions[symbol]
                    log(f"⚠️ Kısmi satış sonrası miktar ({remaining_qty:.6f}) önemsiz, pozisyon tamamen kapatıldı: {symbol}")
                else:
                    self.paper_positions[symbol]['quantity'] = remaining_qty
                    # FIX: Update partial_exit_executed flag
                    self.paper_positions[symbol]['partial_exit_executed'] = True
                    log(f"📉 Kısmi Satış Sonrası Kalan Miktar ({symbol}): {remaining_qty:.6f}")
            else:
                del self.paper_positions[symbol]
            
        if not self.is_live:
            revenue = price * quantity
            self.paper_balance += revenue
            log(f"🧪 Sanal Bakiye Güncellendi: {self.paper_balance:.2f} (+{revenue:.2f})")

        # Sipariş Geçmişine Ekle
        order_record = {
            'timestamp': time.time(),
            'symbol': symbol,
            'action': 'PARTIAL_SELL' if is_partial else 'SELL',
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
        """
        Günlük zarar limitini ve Minimum Bakiye (Hard Stop) kontrol eder.
        
        Returns:
            bool: Eğer True dönerse bot durmalı.
        """
        # 0. Global Hard Stop (Survival Mode)
        # Eğer toplam bakiye $5.0'ın altına düşerse botu zorla durdur.
        # Bu, kalan son parayı komisyonlara kaptırmamak için son çaredir.
        if self.is_live and not self.is_tr:
             total_balance = await self.get_total_balance()
             # Sadece 0.1'den büyük ve 5'ten küçükse durdur (Hata durumunda 0 dönebilir)
             if 0.1 < total_balance < 5.0:
                 log(f"💀 CRITICAL WARNING: Bakiye kritik seviyenin altında (${total_balance:.2f} < $5.00). Bot durduruluyor.")
                 return True

        # 1. Günlük başlangıç bakiyesini belirle (Eğer yoksa)
        if 'daily_start_balance_date' not in self.stats:
             self.stats['daily_start_balance_date'] = ""
             self.stats['daily_start_balance'] = 0.0

        today_str = datetime.now().strftime('%Y-%m-%d')
        if self.stats['daily_start_balance_date'] != today_str:
            # Yeni gün
            current_balance = await self.get_total_balance()
            self.stats['daily_start_balance'] = current_balance
            self.stats['daily_start_balance_date'] = today_str
            self.state_manager.save_stats(self.stats)
            log(f"📅 Yeni Gün: {today_str}. Başlangıç Bakiyesi: ${current_balance:.2f}")
            return False
            
        # 2. Anlık bakiye ile karşılaştır
        start_balance = self.stats['daily_start_balance']
        if start_balance <= 0: return False
        
        # Sadece realized PnL kontrolü yerine Total Equity drawdown kontrolü daha güvenli
        current_balance = await self.get_total_balance()
        drawdown_pct = (start_balance - current_balance) / start_balance
        
        # Fix: Yüzdesel karşılaştırma için 100 ile çarpıyoruz
        if (drawdown_pct * 100) >= self.max_daily_loss:
            log(f"🛑 GÜNLÜK ZARAR LİMİTİ AŞILDI! (Limit: %{self.max_daily_loss}, Mevcut: %{drawdown_pct*100:.2f})")
            log(f"📉 Başlangıç: ${start_balance:.2f} -> Mevcut: ${current_balance:.2f}")
            return True

        # Legacy check (Realized PnL based – daily_realized_pnl zaten yüzdesel toplam)
        pnl_pct = self.stats.get('daily_realized_pnl', 0.0)
        if pnl_pct <= -self.max_daily_loss:
             log(f"🛑 Günlük (Realized) zarar limiti aşıldı: %{pnl_pct:.2f}")
             return True
             
        return False

    async def close(self):
        """Kaynakları temizle"""
        log("Executor kapatılıyor...")
        # Tüm state yapısını (full_state) kaydet
        self.save_positions()
        self.state_manager.save_stats(self.stats)
        if self.is_tr and self.exchange_spot:
             self.exchange_spot.close()

    def stop(self):
        """Executor'ı durdur"""
        log("Executor durduruluyor...")
        self.save_positions()
        self.state_manager.save_stats(self.stats)
