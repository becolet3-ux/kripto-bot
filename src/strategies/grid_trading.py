from typing import List, Dict
import numpy as np
import math

class GridTrading:
    """Yatay piyasalarda grid trading stratejisi"""
    
    def __init__(self, 
                 grid_levels: int = 10,
                 price_range_pct: float = 5.0,
                 profit_per_grid: float = 0.5):
        self.grid_levels = grid_levels
        self.price_range_pct = price_range_pct
        self.profit_per_grid = profit_per_grid
        self.active_grids = {}
    
    def setup_grid(self, symbol: str, current_price: float, total_capital: float, step_size: float = 1.0, min_qty: float = 0.0) -> List[Dict]:
        """Grid seviyelerini oluştur"""
        
        # Fiyat aralığını belirle
        upper_bound = current_price * (1 + self.price_range_pct / 100)
        lower_bound = current_price * (1 - self.price_range_pct / 100)
        
        # Grid seviyelerini hesapla
        price_levels = np.linspace(lower_bound, upper_bound, self.grid_levels)
        
        # Her seviye için sermaye payı
        capital_per_level = total_capital / self.grid_levels
        
        grids = []
        for i, price in enumerate(price_levels):
            # Miktar hesabı (Precision uygulanmış)
            raw_qty = capital_per_level / price
            quantity = raw_qty
            
            if step_size > 0:
                # Step size'a göre yuvarla (aşağı)
                precision = int(round(-math.log10(step_size)))
                quantity = math.floor(raw_qty / step_size) * step_size
                quantity = round(quantity, precision)
            
            # Minimum miktar kontrolü
            if quantity < min_qty:
                # Eğer miktar minimumun altındaysa, bu seviyeyi pas geç veya min_qty yap (riskli olabilir)
                # Şimdilik 0 yapalım, place_grid_orders'da filtrelenir
                quantity = 0.0

            grids.append({
                'level': i,
                'buy_price': price,
                'sell_price': price * (1 + self.profit_per_grid / 100),
                'quantity': quantity,
                'status': 'PENDING',
                'order_id': None,
                'completed_cycles': 0
            })
        
        self.active_grids[symbol] = grids
        return grids
    
    async def place_grid_orders(self, symbol: str, executor):
        """Grid emirlerini yerleştir"""
        
        if symbol not in self.active_grids:
            return
        
        grids = self.active_grids[symbol]
        
        # Bakiye kontrolü
        pending_grids = [g for g in grids if g['status'] == 'PENDING']
        if not pending_grids:
            return

        # Toplam gerekli bakiye (tahmini)
        total_needed = sum(g['quantity'] * g['buy_price'] for g in pending_grids)
        try:
            free_balance = await executor.get_free_balance('TRY')
        except:
            free_balance = 0.0

        if free_balance < total_needed:
            print(f"⚠️ Yetersiz Bakiye ({free_balance:.2f} TRY < {total_needed:.2f} TRY). Sadece bakiye yettiği kadar grid açılacak.")

        current_spent = 0.0
        
        for grid in grids:
            # Sadece henüz işlem yapılmamış gridler için
            if grid['status'] == 'PENDING':
                # Bakiye yetti mi kontrolü (her emir öncesi)
                cost = grid['quantity'] * grid['buy_price']
                if current_spent + cost > free_balance:
                    print(f"⚠️ Bakiye limitine ulaşıldı. Grid {grid['level']} ve sonrası atlanıyor.")
                    break

                try:
                    # Alım emri
                    buy_order = await executor.place_limit_order(
                        symbol=symbol,
                        side='BUY',
                        price=grid['buy_price'],
                        quantity=grid['quantity']
                    )
                    
                    if buy_order:
                        grid['buy_order_id'] = buy_order.get('orderId')
                        grid['status'] = 'BUY_PENDING'
                        
                        # Miktarı güncelle (Precision sonrası gerçek miktar)
                        if 'origQty' in buy_order:
                            grid['quantity'] = float(buy_order['origQty'])
                        
                        current_spent += cost
                    else:
                        # Emir başarısız olduysa (örn: Min miktar hatası), pas geç
                        print(f"⚠️ Grid {grid['level']} emri girilemedi.")
                        pass
                        
                except Exception as e:
                    print(f"Error placing grid order for {symbol}: {e}")
    
    async def check_grid_status(self, symbol: str, current_price: float, executor):
        """Grid durumunu kontrol et ve satış emirleri ver"""
        
        if symbol not in self.active_grids:
            return
        
        grids = self.active_grids[symbol]
        
        for grid in grids:
            # Alım emri gerçekleştiyse satış emri ver
            if grid['status'] == 'BUY_FILLED':
                try:
                    sell_order = await executor.place_limit_order(
                        symbol=symbol,
                        side='SELL',
                        price=grid['sell_price'],
                        quantity=grid['quantity']
                    )
                    
                    if sell_order:
                        grid['sell_order_id'] = sell_order['orderId']
                        grid['status'] = 'SELL_PENDING'
                except Exception as e:
                    print(f"Error placing sell order for {symbol}: {e}")
            
            # Satış tamamlandıysa yeni alım emri
            elif grid['status'] == 'SELL_FILLED':
                try:
                    # Grid tamamlandı, döngü sayısını artır
                    grid['completed_cycles'] += 1
                    
                    # Yeniden alım emri ver
                    buy_order = await executor.place_limit_order(
                        symbol=symbol,
                        side='BUY',
                        price=grid['buy_price'],
                        quantity=grid['quantity']
                    )
                    
                    if buy_order:
                        grid['buy_order_id'] = buy_order['orderId']
                        grid['status'] = 'BUY_PENDING'
                except Exception as e:
                    print(f"Error recycling grid for {symbol}: {e}")
            
            # TODO: Gerçek uygulamada emir durumlarını API'den sorgulamak gerekir.
            # Burada executor'ın order update mekanizması ile entegre olunmalı.
    
    def calculate_grid_profit(self, symbol: str) -> float:
        """Grid'den elde edilen toplam kârı hesapla"""
        
        if symbol not in self.active_grids:
            return 0
        
        total_profit = 0
        grids = self.active_grids[symbol]
        
        for grid in grids:
            if grid.get('completed_cycles', 0) > 0:
                profit_per_cycle = (grid['sell_price'] - grid['buy_price']) * grid['quantity']
                total_profit += profit_per_cycle * grid['completed_cycles']
        
        return total_profit
