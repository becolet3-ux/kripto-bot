import requests
import hashlib
import hmac
import time
import urllib.parse
from typing import Optional, Dict, Any, List
from config.settings import settings

class BinanceTRClient:
    """
    Custom Binance TR API Client based on the provided documentation.
    Supports Spot Trading, Balances, and Market Data.
    Synchronous implementation using requests (to avoid aiohttp SSL issues on Windows).
    """
    
    BASE_URL = "https://www.binance.tr"
    
    def __init__(self, api_key=None, api_secret=None):
        import os
        self.api_key = api_key or os.getenv("BINANCE_TR_API_KEY") or settings.BINANCE_API_KEY
        self.secret_key = api_secret or os.getenv("BINANCE_TR_API_SECRET") or settings.BINANCE_SECRET_KEY
        self.base_url = "https://www.binance.tr"
        self.market_url = "https://api.binance.me"
        self.session = requests.Session()

    def close(self):
        if self.session:
            self.session.close()

    def _sign(self, params: Dict[str, Any]) -> str:
        """
        Generates HMAC SHA256 signature for parameters.
        """
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _market_request(self, endpoint: str, params: dict = None):
        """
        Helper for public market data requests using api.binance.me (more reliable)
        """
        url = f"{self.market_url}{endpoint}"
        
        # Adjust symbol format for Global API (remove underscore)
        if params and "symbol" in params:
            params["symbol"] = params["symbol"].replace("_", "")
            
        try:
            response = self.session.get(url, params=params, verify=True)
            if response.status_code == 200:
                return {"code": 0, "data": response.json()}
            else:
                return {"code": response.status_code, "msg": response.text}
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    def _request(self, method: str, endpoint: str, signed: bool = False, params: Dict = None, base_url: str = None) -> Any:
        if base_url:
            url = f"{base_url}{endpoint}"
        else:
            url = f"{self.base_url}{endpoint}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Always add API Key if available
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
            
        if method != 'GET':
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        if params is None:
            params = {}

        if signed:
            # Add timestamp and recvWindow
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            
            # Generate query string manually to ensure signature consistency
            query_string = urllib.parse.urlencode(params)
            
            # Generate signature using the exact query string
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Append params and signature to URL directly
            url = f"{url}?{query_string}&signature={signature}"
            params = None # Do not pass params to requests, as they are now in URL

        # Retry logic for 1008/Connection errors
        max_retries = 3
        last_resp = None
        
        for attempt in range(max_retries):
            try:
                # Use verify=True for better security and potentially less blocking
                # If SSL fails, user might need to install certs, but usually works on modern Windows
                response = self.session.request(method, url, params=params, headers=headers, verify=True)
                
                try:
                    resp_json = response.json()
                except:
                    resp_json = {"msg": response.text}
                
                last_resp = resp_json

                if response.status_code >= 400:
                    # Don't raise immediately if it's 1008, check code below
                    if str(resp_json.get('code')) != '1008':
                         print(f"❌ API Error ({response.status_code}) on {url}: {resp_json}")
                         # raise Exception(f"Binance TR API Error: {resp_json.get('msg', 'Unknown')}")
                
                # Check for 1008
                if isinstance(resp_json, dict) and str(resp_json.get('code')) == '1008':
                     if attempt < max_retries - 1:
                         print(f"⚠️ Encountered 1008 Error. Retrying ({attempt+1}/{max_retries})...")
                         time.sleep(1)
                         continue
                     else:
                         print(f"❌ Failed after {max_retries} attempts with 1008.")
                         return resp_json # Return the error response
                     
                return resp_json
                
            except Exception as e:
                print(f"❌ Request Failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise
        
        return last_resp

    # --- Public Endpoints ---
    
    def get_time(self):
        return self._request("GET", "/open/v1/common/time")

    def get_symbols(self):
        return self._request("GET", "/open/v1/common/symbols")

    def get_exchange_info(self):
        """
        Standardizes the response to match typical 'exchange_info' format (symbols list)
        """
        resp = self.get_symbols()
        if resp.get('code') == 0 and 'data' in resp:
            # Map 'list' to 'symbols' to be compatible with standard binance parsers
            return {'symbols': resp['data'].get('list', [])}
        return {'symbols': []}

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Converts CCXT format (BTC/USDT) to Binance TR format (BTC_USDT).
        """
        return symbol.replace('/', '_')

    def get_ticker_24hr(self, symbol: str):
        norm_symbol = self._normalize_symbol(symbol)
        # Try Global API first (more reliable)
        resp = self._market_request("/api/v3/ticker/24hr", params={"symbol": norm_symbol})
        if resp.get('code') == 0:
             return resp
        return self._request("GET", "/open/v1/ticker/24hr", params={"symbol": norm_symbol})

    def get_top_symbols(self, limit: int = 100, quote_asset: str = 'TRY') -> List[str]:
        """
        Fetches top N symbols by volume from Binance TR.
        Uses Global API for volume data and TR API for symbol availability.
        """
        # 1. Get TR Symbols
        tr_resp = self.get_symbols()
        if tr_resp.get('code') != 0:
            print("❌ Failed to fetch TR symbols")
            return []
        
        tr_symbols_data = tr_resp.get('data', {}).get('list', [])
        # Filter for active spot pairs with matching quote asset
        active_tr_symbols = {
            s['symbol'].replace('_', ''): s['symbol'] 
            for s in tr_symbols_data 
            if s.get('spotTradingEnable') == 1 and s.get('quoteAsset') == quote_asset
        }
        
        # Exclude Stablecoin pairs (e.g. USDT_TRY) as they are not suitable for this strategy
        excluded = ['USDT_TRY', 'USDC_TRY', 'FDUSD_TRY', 'TUSD_TRY', 'BUSD_TRY', 'DAI_TRY']
        for ex in excluded:
            ex_clean = ex.replace('_', '')
            if ex_clean in active_tr_symbols:
                del active_tr_symbols[ex_clean]
        
        if not active_tr_symbols:
             print(f"❌ No active TR symbols found for {quote_asset}")
             return []

        # 2. Get Global Ticker Stats (for Volume)
        global_resp = self._market_request("/api/v3/ticker/24hr")
        if global_resp.get('code') != 0:
             print("❌ Failed to fetch Global 24hr ticker")
             return list(active_tr_symbols.values())[:limit]
             
        global_tickers = global_resp.get('data', [])
        if not isinstance(global_tickers, list):
             return list(active_tr_symbols.values())[:limit]

        # 3. Match and Sort
        scored_symbols = []
        for t in global_tickers:
            g_sym = t['symbol']
            if g_sym in active_tr_symbols:
                try:
                    vol = float(t.get('quoteVolume', 0))
                    tr_sym = active_tr_symbols[g_sym]
                    scored_symbols.append((tr_sym, vol))
                except:
                    pass
        
        # Sort by volume desc
        scored_symbols.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        top_symbols = [s[0] for s in scored_symbols[:limit]]
        print(f"✅ Found {len(top_symbols)} top volume symbols for {quote_asset}")
        return top_symbols

    def get_ticker_price(self, symbol: str):
        # Use 24hr ticker to get last price, more reliable than trades
        resp = self.get_ticker_24hr(symbol)
        if resp and resp.get('code') == 0:
            data = resp.get('data')
            # Data can be list (if no symbol) or dict (if symbol provided)
            if isinstance(data, list) and len(data) > 0:
                return float(data[0]['lastPrice'])
            elif isinstance(data, dict):
                return float(data.get('lastPrice', 0))
        
        # Fallback to recent trades
        norm_symbol = self._normalize_symbol(symbol)
        trades = self.get_recent_trades(norm_symbol, limit=1)
        if trades and 'data' in trades and len(trades['data']) > 0:
             return float(trades['data'][0]['price'])
        return 0.0

    def get_recent_trades(self, symbol: str, limit: int = 5):
        # Handle Type 1 (Main) vs Type 2/3 (Next)
        if '/' in symbol:
            symbol = self._normalize_symbol(symbol)
            
        type1_pairs = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'BNB_USDT', 'XRP_USDT', 'AVAX_USDT']
        
        if symbol in type1_pairs:
            clean_symbol = symbol.replace('_', '')
            return self._request("GET", "/api/v3/trades", params={"symbol": clean_symbol, "limit": limit}, base_url="https://api.binance.me")
        else:
            return self._request("GET", "/open/v1/market/trades", params={"symbol": symbol, "limit": limit})

    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100):
        norm_symbol = self._normalize_symbol(symbol)
        params = {
            "symbol": norm_symbol,
            "interval": interval,
            "limit": limit
        }
        
        # Try Global API first
        resp = self._market_request("/api/v3/klines", params=params)
        if resp.get('code') == 0:
             return resp
             
        return self._request("GET", "/open/v1/market/klines", params=params)

    # --- Private (Signed) Endpoints ---

    def get_account_info(self):
        """
        Get current account information (Balances).
        """
        return self._request("GET", "/open/v1/account/spot", signed=True)

    def get_exchange_info(self):
        """
        Get exchange info (filters, symbols) from Global API (more detailed).
        """
        return self._market_request("/api/v3/exchangeInfo")

    def new_order(self, symbol: str, side: str, type: str, quantity: float, price: float = None, params: Dict = None):
        """
        Alias for create_order to match ccxt/standard naming.
        """
        return self.create_order(symbol, side, type, quantity, price, params)

    def create_order(self, symbol: str, side: str, type: str, quantity: float, price: float = None, params: Dict = None):
        """
        Creates a new order.
        side: 'BUY' or 'SELL'
        type: 'LIMIT' or 'MARKET'
        """
        norm_symbol = self._normalize_symbol(symbol)
        
        # Binance TR Open API v1 uses Integer values (0=BUY, 1=SELL, 1=LIMIT, 2=MARKET)
        # Documentation Reference: "Order side (side): 0 BUY, 1 SELL", "Order types: 1 LIMIT, 2 MARKET"
        side_int = 0 if side.upper() == 'BUY' else 1
        type_int = 1 if type.upper() == 'LIMIT' else 2
        
        req_params = {
            "symbol": norm_symbol,
            "side": side_int,
            "type": type_int,
            "quantity": quantity
        }
        
        if price:
            req_params["price"] = price
            
        # Merge additional params if provided
        if params:
            # Filter out timeInForce if present, as it's not supported in /open/v1/orders request
            # (Defaults to GTC effectively for Limit orders in this API version)
            safe_params = params.copy()
            if 'timeInForce' in safe_params:
                del safe_params['timeInForce']
            req_params.update(safe_params)
            
        return self._request("POST", "/open/v1/orders", signed=True, params=req_params)

    # --- CCXT Compatibility Layer ---

    def fetch_balance(self):
        """
        CCXT-compatible fetch_balance
        """
        resp = self.get_account_info()
        result = {'info': resp, 'free': {}, 'used': {}, 'total': {}}
        
        if resp.get('code') == 0:
            data = resp.get('data')
            assets = []
            
            # Handle list (some endpoints) vs dict with accountAssets (others)
            if isinstance(data, list):
                assets = data
            elif isinstance(data, dict):
                assets = data.get('accountAssets', [])
                
            for asset in assets:
                code = asset.get('asset')
                free = float(asset.get('free', 0))
                locked = float(asset.get('locked', 0))
                
                if free > 0 or locked > 0:
                    result['free'][code] = free
                    result['used'][code] = locked
                    result['total'][code] = free + locked
        return result

    def fetch_ticker(self, symbol: str):
        """
        CCXT-compatible fetch_ticker
        """
        price = self.get_ticker_price(symbol)
        return {
            'symbol': symbol,
            'last': price,
            'close': price,
            'timestamp': int(time.time() * 1000)
        }
    
    def load_markets(self):
        """
        Mock load_markets for compatibility
        """
        pass

    def create_market_buy_order(self, symbol: str, amount: float, params: Dict = None):
        return self.create_order(symbol, 'BUY', 'MARKET', quantity=amount, params=params)

    def create_market_sell_order(self, symbol: str, amount: float, params: Dict = None):
        return self.create_order(symbol, 'SELL', 'MARKET', quantity=amount, params=params)

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100):
        """
        CCXT-compatible fetch_ohlcv
        Returns list of [timestamp, open, high, low, close, volume]
        """
        resp = self.get_klines(symbol, interval=timeframe, limit=limit)
        ohlcv = []
        if resp and resp.get('code') == 0:
            data = resp.get('data', {})
            # Handle both list (standard) and dict with list (Binance TR)
            klines = data if isinstance(data, list) else data.get('list', [])
            
            for k in klines:
                # Binance TR kline format: [time, open, high, low, close, volume, ...]
                ohlcv.append([
                    int(k[0]),       # Timestamp
                    float(k[1]),     # Open
                    float(k[2]),     # High
                    float(k[3]),     # Low
                    float(k[4]),     # Close
                    float(k[5])      # Volume
                ])
        else:
            print(f"❌ Error fetching OHLCV for {symbol}: {resp}")
        return ohlcv
