import ccxt
import asyncio
import random
import time
from typing import Dict, List, Optional
from config.settings import settings
from src.collectors.binance_tr_client import BinanceTRClient
from src.utils.rate_limiter import RateLimiter
from src.utils.circuit_breaker import CircuitBreaker

class BinanceDataLoader:
    def __init__(self):
        self.mock = settings.USE_MOCK_DATA
        self.is_tr = settings.IS_TR_BINANCE
        
        # Caching & Rate Limiting
        self._cache = {}
        self.rate_limiter = RateLimiter(max_requests=1200, time_window=60)
        self.circuit_breaker = CircuitBreaker()
        
        if not self.mock:
            if self.is_tr:
                print("🇹🇷 Using Binance TR Client (Sync)")
                self.exchange = BinanceTRClient()
            else:
                mode = 'future' if settings.TRADING_MODE == 'futures' else 'spot'
                print(f"🌍 Using Binance Global Client (Sync CCXT) - Mode: {mode.upper()}")
                
                # Fetch keys directly from env to ensure they are loaded
                import os
                api_key = os.getenv("BINANCE_API_KEY", settings.BINANCE_API_KEY)
                secret_key = os.getenv("BINANCE_SECRET_KEY", settings.BINANCE_SECRET_KEY)
                
                self.exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': secret_key,
                    'enableRateLimit': True,
                    'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'verify': False, # Disable SSL verification
                    'timeout': 30000,
                    'options': {
                        'defaultType': mode, # 'spot' or 'future'
                    }
                })
        
    async def initialize(self):
        """Load markets"""
        if not self.mock:
            try:
                if self.is_tr:
                    # TR Client doesn't need load_markets yet, but we can verify connection
                    await asyncio.to_thread(self.exchange.get_time)
                    print("✅ Binance TR Initialized")
                else:
                    await asyncio.wait_for(asyncio.to_thread(self.exchange.load_markets), timeout=30.0)
            except Exception as e:
                print(f"Authenticated load_markets failed: {e}")
                if not self.is_tr:
                    print("Retrying with Public Client for Data Loading...")
                    # Re-init as public (no keys)
                    self.exchange = ccxt.binance({
                        'enableRateLimit': True,
                        'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'verify': False, # Disable SSL verification
                        'timeout': 60000, # Increase timeout for large exchangeInfo
                        'options': {'defaultType': 'future' if settings.TRADING_MODE == 'futures' else 'spot'}
                    })
                    try:
                        await asyncio.wait_for(asyncio.to_thread(self.exchange.load_markets), timeout=30.0)
                        print("✅ Public Client Initialized (Real Data)")
                    except Exception as e2:
                        print(f"Public connect failed: {repr(e2)}. Switching to Mock Mode.")
                        self.mock = True
                else:
                    print(f"Failed to connect ({e}). Switching to Mock Mode.")
                    self.mock = True
        
    async def close(self):
        # Sync ccxt doesn't need close
        pass

    async def get_current_price(self, symbol: str) -> float:
        if self.mock:
            base = 95000 if 'BTC' in symbol else 2700
            return base + random.uniform(-50, 50)
            
        ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
        return float(ticker['last'])

    async def get_funding_rate(self, symbol: str) -> Dict:
        if self.mock:
            return {
                'symbol': symbol,
                'fundingRate': 0.0001,
                'fundingTimestamp': int(time.time() * 1000),
                'nextFundingTime': int(time.time() * 1000) + 28800000
            }

        try:
            funding_info = await asyncio.to_thread(self.exchange.fetch_funding_rate, symbol)
            return {
                'symbol': symbol,
                'fundingRate': funding_info['fundingRate'],
                'fundingTimestamp': funding_info['timestamp'],
                'nextFundingTime': funding_info['fundingTimestamp'] + 28800000
            }
        except Exception as e:
            # If futures fetch fails (e.g. permission error), return 0 funding
            # This allows the bot to continue in Spot-Only mode
            # print(f"Error fetching funding rate for {symbol}: {e}")
            return {
                'symbol': symbol,
                'fundingRate': 0.0,
                'fundingTimestamp': int(time.time() * 1000),
                'nextFundingTime': int(time.time() * 1000) + 28800000
            }

    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100, use_cache: bool = True) -> List[List]:
        # DEBUG LOG
        print(f"DEBUG: get_ohlcv {symbol} Mock={self.mock}")
        
        if self.mock:
            # Generate mock OHLCV
            now = int(time.time() * 1000)
            data = []
            base_price = 95000 if 'BTC' in symbol else 2700
            for i in range(limit):
                ts = now - (limit - i) * 3600000
                o = base_price + random.uniform(-50, 50)
                c = o + random.uniform(-20, 20)
                h = max(o, c) + random.uniform(0, 10)
                l = min(o, c) - random.uniform(0, 10)
                v = random.uniform(1, 100)
                data.append([ts, o, h, l, c, v])
            return data
            
        # Cache Check
        cache_key = f"{symbol}_{timeframe}"
        now = time.time()
        
        if use_cache and cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            # 30 seconds cache validity to prevent redundant calls in same scan cycle
            if now - timestamp < 30: 
                return data

        # Rate Limit Enforcer
        await self.rate_limiter.wait_if_needed()
        
        try:
            # Circuit Breaker Wrapping
            # We run circuit_breaker.call inside the thread to handle sync exceptions properly
            def _fetch():
                return self.circuit_breaker.call(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
            
            data = await asyncio.to_thread(_fetch)
            
            # Update Cache
            if data:
                last_ts = data[-1][0]
                readable_ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_ts/1000))
                print(f"DEBUG: {symbol} Last Candle Time: {readable_ts} | Close: {data[-1][4]}")
                self._cache[cache_key] = (data, time.time())
            return data
        except Exception as e:
            # print(f"⚠️ Fetch Error {symbol}: {e}")
            return []
