import numpy as np
from typing import Dict, Optional

class DynamicPositionSizer:
    """Volatilite bazlı pozisyon boyutlandırma"""
    
    def __init__(self, base_position_pct: float = 20.0, max_position_pct: float = 30.0, min_position_pct: float = 10.0):
        self.base_position_pct = base_position_pct
        self.max_position_pct = max_position_pct
        self.min_position_pct = min_position_pct
    
    def calculate_position_size(self, 
                               symbol: str,
                               balance: float,
                               volatility: float,
                               confidence_score: float,
                               correlation_with_portfolio: float = 0.0) -> Dict:
        """Dinamik pozisyon büyüklüğü hesapla"""
        
        # 1. Volatilite ayarlaması
        # Düşük volatilite = Daha büyük pozisyon
        # Yüksek volatilite = Daha küçük pozisyon
        volatility_factor = 1.0 - min(volatility / 100, 0.5)  # Max %50 düşüş
        
        # 2. Güven skoru ayarlaması
        # Yüksek skor = Daha büyük pozisyon
        confidence_factor = confidence_score / 10.0  # 0-1 arası normalize
        
        # 3. Korelasyon ayarlaması
        # Yüksek korelasyon = Daha küçük pozisyon (çeşitlendirme için)
        correlation_penalty = 1.0 - (abs(correlation_with_portfolio) * 0.5)
        
        # Toplam faktör
        total_factor = volatility_factor * confidence_factor * correlation_penalty
        
        # Pozisyon yüzdesi hesapla
        position_pct = self.base_position_pct * total_factor
        
        # Sınırları uygula
        position_pct = max(self.min_position_pct, min(position_pct, self.max_position_pct))
        
        # Dolar değerine çevir
        position_size = balance * (position_pct / 100)
        
        return {
            'position_size': position_size,
            'position_pct': position_pct,
            'volatility_factor': volatility_factor,
            'confidence_factor': confidence_factor,
            'correlation_penalty': correlation_penalty,
            'final_factor': total_factor
        }
    
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Kelly Criterion ile optimal pozisyon büyüklüğü"""
        
        if avg_loss == 0:
            return 0
        
        win_loss_ratio = abs(avg_win / avg_loss)
        kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # Kelly'nin yarısını kullan (güvenlik için)
        kelly_pct = kelly_pct * 0.5
        
        # Sınırla
        return max(0, min(kelly_pct * 100, self.max_position_pct))
