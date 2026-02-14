from typing import Dict, List, Optional
import pandas as pd
from src.strategies.analyzer import TradeSignal
from src.utils.logger import log
from config.settings import settings
from src.risk.portfolio_optimizer import PortfolioOptimizer

class OpportunityManager:
    """
    Fırsat Maliyeti Yöneticisi (Opportunity Cost Manager).
    
    Amacı:
    Eğer bakiye doluysa (yeni alım yapılamıyorsa),
    mevcut portföydeki "düşük potansiyelli" varlıkları,
    piyasadaki "yüksek potansiyelli" fırsatlarla değiştirmeyi önerir.
    
    Mantık:
    1. Portföydeki her coin için güncel skor hesapla.
    2. Piyasadaki (henüz elimizde olmayan) fırsatları tarar.
    3. Eğer (En İyi Fırsat Skoru - En Kötü Portföy Skoru) > Eşik Değer ise;
       VE (Yeni Fırsat Portföy ile Aşırı Korele Değilse) -> Değişim (Swap) önerir.
    """
    
    def __init__(self, min_score_diff: float = 5.0, min_hold_time: int | None = None):
        self.min_score_diff = min_score_diff
        self.min_hold_time = min_hold_time if min_hold_time is not None else getattr(settings, "OPP_MIN_HOLD_SECONDS", 3600)
        self.portfolio_optimizer = PortfolioOptimizer(correlation_threshold=0.80)

    def check_for_swap_opportunity(self, 
                                 portfolio: Dict, 
                                 market_signals: List[TradeSignal]) -> Optional[Dict]:
        """
        Takas fırsatı olup olmadığını kontrol eder.
        
        Args:
            portfolio: Mevcut pozisyonlar {'BTC_TRY': {'entry_time': ..., 'quantity': ...}}
            market_signals: Piyasadaki güncel sinyaller
            
        Returns:
            None veya {'action': 'SWAP', 'sell_symbol': '...', 'buy_signal': signal_obj}
        """
        if not portfolio:
            return None
            
        # 1. Portföydeki en zayıf halkayı bul
        # Not: Gerçek senaryoda portföydeki coinlerin anlık skorlarını da hesaplamamız gerekir.
        # Şimdilik market_signals içinde portföydeki coinlerin de olduğunu varsayıyoruz.
        
        portfolio_scores = []
        available_opportunities = []
        
        import time
        current_time = time.time()

        # Sinyalleri haritala
        signal_map = {s.symbol: s for s in market_signals}
        
        for symbol, data in portfolio.items():
            # --- PRO FIX: Allow analysis of locked assets for High Score Diff overrides ---
            # Old: if current_time - data.get('timestamp', 0) < self.min_hold_time: continue
            
            hold_time = current_time - data.get('timestamp', 0)
            is_locked = hold_time < self.min_hold_time

            # DUST CHECK: 20 TL altı bakiyeleri takas adayı yapma (Kilitlenmeyi önle)
            est_value = data.get('quantity', 0) * data.get('entry_price', 0)
            if est_value < 20.0:
                 continue
                
            # Eğer portföydeki coinin güncel sinyali yoksa (belki hacim düştü), skoru 0 varsay
            signal = signal_map.get(symbol)
            score = signal.score if signal else 0
            
            portfolio_scores.append({
                'symbol': symbol,
                'score': score,
                'data': data,
                'is_locked': is_locked, # Added flag
                'hold_time': hold_time
            })
            
        if not portfolio_scores:
            return None
            
        # En düşük skorlu (satılmaya aday) coin
        # PRO FIX: BNB/USDT satılmaya aday olamaz (Komisyon indirimi için gerekli)
        valid_candidates = [
            x for x in portfolio_scores 
            if x['symbol'] != "BNB/USDT"
        ]
        
        if not valid_candidates:
             # Sadece BNB varsa ve başka fırsat yoksa bekle
             return None

        worst_asset = min(valid_candidates, key=lambda x: x['score'])
        
        # 2. Piyasadaki en iyi fırsatları bul (Elimizde OLMAYANLAR arasından)
        for signal in market_signals:
            if signal.symbol not in portfolio and signal.action == "ENTRY":
                available_opportunities.append(signal)
                
        if not available_opportunities:
            return None
            
        # Fırsatları skora göre sırala (En yüksekten en düşüğe)
        available_opportunities.sort(key=lambda x: x.score, reverse=True)
        
        # 3. Karşılaştırma ve Korelasyon Kontrolü
        for candidate in available_opportunities:
            score_diff = candidate.score - worst_asset['score']
            
            # --- LOCK CHECK WITH OVERRIDE ---
            if worst_asset['is_locked']:
                # GENERAL RULE: If score difference is MASSIVE (> 20.0), break the lock.
                # SNIPER RULE (Implicit): If we are in sniper mode, we might want even lower threshold (15.0),
                # but 20.0 is a safe "Universal" threshold for "Undeniable Opportunity".
                # Example: Holding Coin A (Score 5) vs Opportunity B (Score 26) -> Diff 21 -> SWAP!
                
                LOCK_BREAK_THRESHOLD = 20.0
                
                if score_diff < LOCK_BREAK_THRESHOLD: 
                    # log(f"🔒 Locked: {worst_asset['symbol']} (Held {int(worst_asset['hold_time'])}s). Diff {score_diff:.1f} < {LOCK_BREAK_THRESHOLD}")
                    break 
                    return None
            
            # Eğer en iyi fırsat bile yeterli fark atmıyorsa, diğerlerine bakmaya gerek yok
            if score_diff <= self.min_score_diff:
                break
                
            # --- Portfolio Correlation Check ---
            # Portföydeki diğer varlıkların fiyat geçmişini topla (Satacağımız hariç)
            portfolio_prices = {}
            for s_sym in portfolio.keys():
                if s_sym == worst_asset['symbol']:
                    continue
                
                s_signal = signal_map.get(s_sym)
                if s_signal and s_signal.details.get('price_history'):
                    portfolio_prices[s_sym] = pd.Series(s_signal.details['price_history'])
            
            candidate_prices = pd.Series(candidate.details.get('price_history', []))
            
            # Risk Analizi
            risk_analysis = self.portfolio_optimizer.check_correlation_risk(
                portfolio_prices,
                candidate.symbol,
                candidate_prices
            )
            
            if risk_analysis['is_safe']:
                # Loglama (Debug için)
                # log(f"Swap Onaylandı: {worst_asset['symbol']} -> {candidate.symbol} (Fark: {score_diff:.1f})")
                
                return {
                    'action': 'SWAP',
                    'sell_symbol': worst_asset['symbol'],
                    'buy_signal': candidate,
                    'reason': f"Better opportunity (Score diff: {score_diff:.1f}) & Safe Correlation"
                }
            else:
                # Riskli ise logla ve bir sonraki adaya geç
                # log(f"Swap Reddedildi (Risk): {candidate.symbol} is correlated with {risk_analysis['correlated_with']}")
                continue
                
        return None

    def analyze_swap_status(self, portfolio: Dict, market_signals: List[TradeSignal], score_cache: Dict[str, float] = None) -> Dict:
        """
        Detaylı swap analizi durumu döndürür (Raporlama için).
        """
        if not portfolio:
             return {"action": "WAIT", "reason": "Portföy boş, yeni fırsatlar aranıyor.", "details": {}}

        import time
        current_time = time.time()
        
        # 1. Portföy Analizi
        portfolio_scores = []
        signal_map = {s.symbol: s for s in market_signals}
        score_cache = score_cache or {}
        
        for symbol, data in portfolio.items():
            signal = signal_map.get(symbol)
            score_source = "fresh"
            
            # Use cached score if current signal is missing (prevent Score 0 during partial scans)
            # If both missing, default to -10.0 ONLY IF it's not a fresh buy.
            # However, for analyze_swap_status, we want to be honest about missing data.
            # But "0" implies "Neutral", which is misleading if it's actually "Unknown".
            
            if signal:
                score = signal.score
            else:
                if symbol in score_cache:
                    score = score_cache[symbol]
                    score_source = "cached"
                else:
                    # PRO FIX: Eksik veri cezası -100 yerine 0 (Nötr) yapıldı.
                    # Ayrıca BNB/USDT için özel koruma.
                    if symbol == "BNB/USDT":
                         score = 0.0 # BNB her zaman nötr kalmalı (Base asset)
                         score_source = "base_asset_protection"
                    else:
                         score = 0.0 # Bilinmeyen varlık nötr kabul edilir
                         score_source = "missing_data"
                # If truly unknown, maybe mark it? But 0 is safe for comparison.
            
            # Hold time check
            hold_time = current_time - data.get('timestamp', 0)
            is_locked = hold_time < self.min_hold_time
            
            portfolio_scores.append({
                'symbol': symbol,
                'score': score,
                'score_source': score_source,
                'is_locked': is_locked,
                'hold_time': hold_time
            })
            
        if not portfolio_scores:
            return {"action": "WAIT", "reason": "Portföy verisi analiz edilemedi.", "details": {}}

        worst_asset = min(portfolio_scores, key=lambda x: x['score'])

        # 2. Market Fırsat Analizi
        available_opportunities = []
        for signal in market_signals:
            if signal.symbol not in portfolio and signal.action == "ENTRY":
                available_opportunities.append(signal)
        
        if not available_opportunities:
             return {
                 "action": "HOLD", 
                 "reason": "Piyasada daha iyi bir fırsat bulunamadı.", 
                 "details": {"worst_asset": worst_asset}
             }

        best_opportunity = max(available_opportunities, key=lambda x: x.score)
        score_diff = best_opportunity.score - worst_asset['score']
        
        # 3. Karar
        details = {
            "worst_asset": worst_asset,
            "best_opportunity": {
                "symbol": best_opportunity.symbol,
                "score": best_opportunity.score
            },
            "score_diff": score_diff,
            "threshold": self.min_score_diff
        }

        if worst_asset['is_locked']:
            LOCK_BREAK_THRESHOLD = getattr(settings, "OPP_LOCK_BREAK_DIFF", 20.0)
            if score_diff >= LOCK_BREAK_THRESHOLD:
                return {
                    "action": "SWAP_READY",
                    "reason": "OPPORTUNITY_OVERRIDE_LOCKED_ASSET",
                    "details": details
                }
            return {
                "action": "HOLD",
                "reason": "ASSET_LOCKED_MIN_HOLD_TIME",
                "details": details
            }

        if score_diff > self.min_score_diff:
            return {
                "action": "SWAP_READY", 
                "reason": f"Fırsat bulundu! {worst_asset['symbol']} -> {best_opportunity.symbol} (Fark: {score_diff:.1f} > {self.min_score_diff})",
                "details": details
            }
        else:
            return {
                "action": "HOLD", 
                "reason": f"Mevcut varlıklar yeterince iyi. En iyi alternatif ({best_opportunity.symbol}) sadece {score_diff:.1f} puan fark attı (Gereken: {self.min_score_diff}).",
                "details": details
            }
