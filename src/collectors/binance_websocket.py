import asyncio
import json
import logging
from binance import AsyncClient, BinanceSocketManager

# Logger kurulumu (basit)
logger = logging.getLogger(__name__)

class BinanceWebSocket:
    """Real-time veri akışı için WebSocket"""
    
    def __init__(self, symbols: list[str]):
        self.symbols = symbols
        self.client = None
        self.bsm = None
        self.price_cache = {}
        self.callbacks = []
        self.running = False
    
    async def start(self):
        """WebSocket bağlantısını başlat"""
        self.running = True
        try:
            self.client = await AsyncClient.create()
            self.bsm = BinanceSocketManager(self.client)
            
            # Multi-symbol ticker stream
            # Binance TR symbols usually differ, but assuming standard format here
            # or converting. If IS_TR is true, we might need a different library or endpoint
            # but for now implementing as per spec using python-binance
            streams = [f"{symbol.lower()}@ticker" for symbol in self.symbols]
            
            logger.info(f"WebSocket connecting for streams: {streams}")
            
            async with self.bsm.multiplex_socket(streams) as stream:
                while self.running:
                    try:
                        msg = await stream.recv()
                        await self.process_message(msg)
                    except Exception as e:
                        logger.error(f"WebSocket stream error: {e}")
                        await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
        finally:
            if self.client:
                await self.client.close_connection()

    def stop(self):
        self.running = False
    
    async def process_message(self, msg: dict):
        """Gelen mesajı işle"""
        if msg.get('data'):
            data = msg['data']
            symbol = data['s']
            try:
                price = float(data['c'])  # Current price
                volume = float(data['v'])  # Volume
                price_change_pct = float(data['P'])  # Price change %
                
                # Cache güncelle
                self.price_cache[symbol] = {
                    'price': price,
                    'volume': volume,
                    'change_pct': price_change_pct,
                    'timestamp': data['E']
                }
                
                # Callback'leri çağır
                for callback in self.callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(symbol, self.price_cache[symbol])
                        else:
                            callback(symbol, self.price_cache[symbol])
                    except Exception as e:
                        logger.error(f"Callback error for {symbol}: {e}")
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing message: {e}")
    
    def register_callback(self, callback):
        """Fiyat güncellemesi için callback kaydet"""
        self.callbacks.append(callback)
    
    def get_latest_price(self, symbol: str) -> dict:
        """En güncel fiyatı getir"""
        return self.price_cache.get(symbol)
