import ccxt
import asyncio
import time
import logging
from typing import Dict, Optional
from config.settings import settings
from src.utils.logger import log

class FundingRateLoader:
    """
    Responsible for fetching and caching funding rates for all symbols efficiently.
    Phase 4: Funding Rate Integration
    """
    def __init__(self):
        self.funding_rates: Dict[str, Dict] = {}
        self.last_update_time = 0
        self.update_interval = 28800 # 8 hours (in seconds)
        self.exchange = None
        
        # Initialize CCXT for Futures
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'options': {'defaultType': 'future'}
            })
        except Exception as e:
            log(f"⚠️ FundingRateLoader Init Error: {e}")

    async def initialize(self):
        """Initial fetch of funding rates"""
        await self.update_funding_rates()

    async def update_funding_rates(self):
        """Fetches funding rates for ALL symbols (Bulk)"""
        if not self.exchange:
            return

        now = time.time()
        # Update only if interval passed
        if now - self.last_update_time < self.update_interval and self.funding_rates:
            return

        try:
            # fetchFundingRates is supported by Binance
            log("🔄 Funding Rates Güncelleniyor (Bulk Fetch)...")
            rates = await asyncio.wait_for(asyncio.to_thread(self.exchange.fetch_funding_rates), timeout=30.0)
            
            # Map by symbol
            count = 0
            for symbol, data in rates.items():
                # Normalize symbol if needed (CCXT returns BTC/USDT:USDT for futures sometimes)
                # We stick to CCXT format or convert to our format (BTC_USDT vs BTC/USDT)
                # Bot uses BTC_TRY or BTC/USDT depending on context. 
                # Let's keep original key and also try to map standard format.
                
                self.funding_rates[symbol] = {
                    'rate': data.get('fundingRate', 0.0),
                    'next_funding_time': data.get('fundingTimestamp', 0),
                    'timestamp': now
                }
                
                # Also support "BTC_USDT" format if CCXT returns "BTC/USDT"
                if '/' in symbol:
                    alt_symbol = symbol.replace('/', '_')
                    self.funding_rates[alt_symbol] = self.funding_rates[symbol]
                    
                count += 1
                
            self.last_update_time = now
            log(f"✅ {count} adet sembol için Funding Rate güncellendi.")
            
        except Exception as e:
            log(f"⚠️ Funding Rate Update Error: {e}")

    def get_funding_rate(self, symbol: str) -> float:
        """Returns the cached funding rate for a symbol. Returns 0.0 if not found."""
        # Try exact match
        data = self.funding_rates.get(symbol)
        
        # Try common variations
        if not data:
            if '_' in symbol:
                data = self.funding_rates.get(symbol.replace('_', '/'))
            elif '/' in symbol:
                data = self.funding_rates.get(symbol.replace('/', '_'))
                
        # Try appending :USDT for futures symbols in CCXT
        if not data:
            if not symbol.endswith(':USDT'):
                # e.g. BTC/USDT -> BTC/USDT:USDT
                data = self.funding_rates.get(f"{symbol}:USDT")
        
        if data:
            return float(data.get('rate', 0.0))
            
        return 0.0

    def get_funding_info(self, symbol: str) -> Dict:
        """Returns full funding info"""
        rate = self.get_funding_rate(symbol)
        # We might need next funding time, but for strategy only rate is critical
        return {'rate': rate}
