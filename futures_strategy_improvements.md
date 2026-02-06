# Kripto Futures Bot İyileştirme Talimatları

Bu prompt'u AI asistanınıza vererek mevcut Binance Global Futures botunuzu adım adım geliştirebilirsiniz.

---

## BAĞLAM
Binance Global Futures üzerinde Long-Only stratejisi ile çalışan bir kripto trading botum var. Bot Python ile yazılmış, CCXT kullanıyor, SuperTrend/RSI/MACD/ADX/CCI/MFI gibi indikatörlere sahip ve 2x kaldıraçla çalışıyor. Şu anda temel buy/sell sinyalleri var ama risk yönetimi ve kar optimizasyonu eksik.

---

## AŞAMA 1: TRAILING STOP LOSS VE KISMI KAR REALİZASYONU (HEMEN UYGULANACAK)

### Görev 1.1: ATR Bazlı Trailing Stop Loss
```
Gereksinimler:
1. Her açılan Long pozisyon için otomatik trailing stop loss hesapla
2. Stop loss seviyesi: Giriş fiyatının altında 2x ATR(14) mesafede başlasın
3. Fiyat yukarı çıktıkça stop loss da yukarı kaysın (trailing)
4. Stop loss asla aşağı inmesin (sadece yukarı)
5. Stop loss tetiklendiğinde pozisyonu market order ile kapat

Teknik Detaylar:
- ATR hesaplaması için ta-lib veya pandas_ta kullan
- Stop loss seviyesini her 1 dakikada güncelle
- Position state'e trailing_stop_price ekle
- Executor'da her cycle'da trailing stop kontrolü yap
```

### Görev 1.2: Kısmi Kar Realizasyonu
```
Gereksinimler:
1. Pozisyon %4 kar ettiğinde otomatik olarak pozisyonun %50'sini kapat
2. Kalan %50'yi trailing stop ile devam ettir
3. Her iki parçayı da ayrı ayrı takip et (split position tracking)

Implementasyon:
- Position nesnesine partial_exit_executed (bool) flag'i ekle
- İlk %4 kar'da check_partial_exit() fonksiyonu tetiklensin
- Binance'e reduceOnly=True ile %50 sell order gönder
- Kalan pozisyon için trailing stop mesafesini 1.5x ATR'ye daralt
```

### Görev 1.3: Time-Based Stop
```
Gereksinimler:
1. Pozisyon açıldıktan 24 saat sonra hala kar etmediyse (%0-%2 arası) otomatik kapat
2. 48 saat sonra hala açıksa kar/zarar durumuna bakılmaksızın kapat

Parametreler:
- max_hold_time_without_profit: 24 saat
- absolute_max_hold_time: 48 saat
- Position state'e entry_timestamp ekle
```

**Beklenen Çıktı Dosyaları:**
- `src/execution/stop_loss_manager.py` (yeni)
- `src/execution/executor.py` (güncellenmiş - stop loss entegrasyonu)
- `src/models/position.py` (güncellenmiş - yeni field'lar)

---

## AŞAMA 2: VOLATILITE BAZLI POZISYON BOYUTLANDIRMA (BU HAFTA)

### Görev 2.1: Dinamik Pozisyon Hesaplayıcı
```
Gereksinimler:
1. Her sembol için real-time volatilite hesapla (ATR / Price yüzdesi)
2. Volatilite düşükse (%1-2) -> Pozisyon boyutu %30-40 bakiye
3. Volatilite ortaysa (%2-4) -> Pozisyon boyutu %20-30 bakiye
4. Volatilite yüksekse (%4+) -> Pozisyon boyutu %10-20 bakiye

Formül:
position_size = (total_balance * base_percentage) / volatility_multiplier

Örnek:
- 1000 USDT bakiye
- BTC volatilite: %2.5 (orta)
- Base: %25
- Hesaplama: 1000 * 0.25 = 250 USDT pozisyon
```

### Görev 2.2: Dinamik Kaldıraç Ayarlayıcı
```
Gereksinimler:
1. Mevcut 2x sabit kaldıracı volatiliteye göre dinamik yap
2. Düşük volatilite -> 3x kaldıraç (daha güvenli)
3. Orta volatilite -> 2x kaldıraç (varsayılan)
4. Yüksek volatilite -> 1x kaldıraç (koruyucu)

Implementasyon:
- Her sembol için kaldıracı pozisyon açılmadan önce set et
- Binance API: exchange.fapiPrivatePostLeverage()
- Kaldıraç değişikliklerini logla
```

**Beklenen Çıktı Dosyaları:**
- `src/risk/position_sizer.py` (yeni)
- `src/risk/volatility_calculator.py` (yeni)
- `src/execution/executor.py` (güncellenmiş - dinamik sizing entegrasyonu)

---

## AŞAMA 3: MARKET REJİM TESPİTİ (BU HAFTA)

### Görev 3.1: Trending vs Ranging Market Detector
```
Gereksinimler:
1. ADX > 25 ve Bollinger Bands genişliği artan -> TRENDING
2. ADX < 20 ve Bollinger Bands genişliği dar -> RANGING
3. Her market rejimine göre farklı strateji parametreleri

Trending Market Modifikasyonları:
- Trailing stop mesafesini artır (3x ATR)
- Kısmi kar realizasyonunu %6'ya çıkar
- Daha agresif pozisyon boyutu (%35)

Ranging Market Modifikasyonları:
- Trailing stop mesafesini daralt (1.5x ATR)
- Kısmi kar realizasyonunu %3'e düşür
- Konservatif pozisyon boyutu (%15)
- Mümkünse işlem yapma (no-trade zone)
```

### Görev 3.2: No-Trade Zone Kuralları
```
Aşağıdaki koşullarda pozisyon AÇMA:
1. ADX < 20 (zayıf trend)
2. RSI 40-60 arası (belirsiz momentum)
3. Price VWAP ± %0.5 içinde (konsolidasyon)
4. Son 4 saatte %1'den az hareket

Bu durumda:
- Sinyal gelirse logla ama işlem yapma
- Mevcut pozisyonları trailing stop ile yönetmeye devam et
```

**Beklenen Çıktı Dosyaları:**
- `src/analysis/market_regime.py` (yeni)
- `src/strategies/regime_adaptive_strategy.py` (yeni)
- `src/brain/brain.py` (güncellenmiş - rejim awareness)

---

## AŞAMA 4: FUNDING RATE ENTEGRASYONU (BU AY)

### Görev 4.1: Funding Rate Collector
```
Gereksinimler:
1. Her 8 saatte bir tüm sembollerin funding rate'ini çek
2. Binance API: exchange.fapiPublicGetPremiumIndex()
3. Funding rate'i veritabanına veya state'e kaydet

Veri Yapısı:
{
  "symbol": "BTC/USDT",
  "funding_rate": 0.0001,  # %0.01
  "next_funding_time": 1234567890,
  "hourly_rate": 0.000033  # 8 saatlik / 8
}
```

### Görev 4.2: Funding Rate Stratejisi
```
Gereksinimler:
1. Funding rate > +0.05% -> Normal Long sinyalini boost et (öncelik +1)
2. Funding rate > +0.10% -> Çok agresif Long, pozisyon boyutunu %20 artır
3. Funding rate < -0.05% -> Long sinyallerini ignore et (negatif funding Long'a maliyetli)

Bonus Sinyal:
- Eğer funding rate pozitif ve artıyorsa, Long pozisyonda tutma süresini uzat
- 8 saat boyunca pozitif funding alarak ekstra kazanç sağla
```

**Beklenen Çıktı Dosyaları:**
- `src/data/funding_rate_loader.py` (yeni)
- `src/strategies/funding_aware_strategy.py` (yeni)
- `src/brain/brain.py` (güncellenmiş - funding bonus)

---

## AŞAMA 5: MULTI-STRATEGY FRAMEWORK (BU AY)

### Görev 5.1: Strategy Enum ve Manager
```
Gereksinimler:
1. Üç ayrı Long-Only alt-stratejisi oluştur:
   - BREAKOUT: Konsolidasyon sonrası kırılımları yakala
   - MEAN_REVERSION: Aşırı düşüşlerden geri dönüşleri yakala
   - MOMENTUM: Güçlü trendleri takip et

2. Her strateji için ayrı sinyal üretici fonksiyon

Breakout Stratejisi:
- Bollinger Bands %10 daralma sonrası genişleme
- Volume spike (son 20 bar ortalamasının 2x'i)
- Üst bant kırılımı

Mean Reversion Stratejisi:
- RSI < 30 ve yükselişe geçiyor
- Price alt Bollinger Band'a değdi ve geri dönüyor
- MACD histogram dibi yaptı

Momentum Stratejisi:
- ADX > 30
- SuperTrend yükseliş sinyali
- MACD golden cross
```

### Görev 5.2: Strategy Voting System
```
Gereksinimler:
1. Her strateji BUY/SELL/HOLD sinyali üretsin
2. Weighted voting: Her stratejinin geçmiş performansına göre ağırlığı olsun
3. Final karar: Ağırlıklı çoğunluk (2/3 konsensüs gerekli)

Örnek:
- Breakout: BUY (weight: 0.4)
- Mean Reversion: HOLD (weight: 0.3)
- Momentum: BUY (weight: 0.3)
- Total: 0.4 + 0.3 = 0.7 > 0.66 threshold -> BUY
```

**Beklenen Çıktı Dosyaları:**
- `src/strategies/breakout_strategy.py` (yeni)
- `src/strategies/mean_reversion_strategy.py` (yeni)
- `src/strategies/momentum_strategy.py` (yeni)
- `src/strategies/strategy_manager.py` (yeni)

---

## AŞAMA 6: GELİŞMİŞ PORTFOLIO YÖNETİMİ (UZUN VADE)

### Görev 6.1: Maksimum Pozisyon Limitleri
```
Gereksinimler:
1. Aynı anda maksimum 4 açık pozisyon
2. Eğer 4 pozisyon doluysa, yeni sinyal için mevcut pozisyonlardan en zayıfını kapat
3. "Zayıf pozisyon" kriterleri:
   - En az kar eden (veya en çok zarar eden)
   - En uzun süredir açık olan
   - En düşük momentum skoruna sahip

Pozisyon Rotasyonu:
- Her yeni sinyal geldiğinde mevcut pozisyonları score'la
- Yeni sinyalin score'u > mevcut en düşük score -> Swap yap
```

### Görev 6.2: Kategori/Sektör Limitleri
```
Gereksinimler:
1. Coinleri kategorize et (Layer-1, DeFi, Meme, AI vb.)
2. Her kategoriye maksimum sermaye limiti:
   - Layer-1: Max %40
   - DeFi: Max %30
   - Meme: Max %20
   - AI: Max %30

3. Eğer bir kategoride limit doluysa o kategoriden yeni pozisyon açma

Kategori Tanımları (hardcode veya JSON):
{
  "Layer-1": ["BTC", "ETH", "SOL", "ADA", "AVAX"],
  "DeFi": ["UNI", "AAVE", "CRV", "SNX"],
  "Meme": ["DOGE", "SHIB", "PEPE"],
  "AI": ["FET", "AGIX", "RNDR"]
}
```

**Beklenen Çıktı Dosyaları:**
- `src/risk/portfolio_manager.py` (yeni)
- `src/config/asset_categories.json` (yeni)
- `src/execution/executor.py` (güncellenmiş - portfolio limits)

---

## AŞAMA 7: MACHINE LEARNING ENTEGRASYONU (UZUN VADE)

### Görev 7.1: Feature Engineering
```
Gereksinimler:
1. Mevcut tüm indikatörleri ML feature'larına dönüştür
2. Ek feature'lar oluştur:
   - Price rate of change (1h, 4h, 24h)
   - Volume ratio (current / MA)
   - Volatility percentile (son 30 gün içinde nerede)
   - Trend strength (ADX * SuperTrend direction)

3. Her trade'den sonra label oluştur:
   - 4 saat içinde %2+ kar -> 1 (başarılı)
   - 4 saat içinde %-1 altı zarar -> 0 (başarısız)
   - Diğer -> None (ignore)

CSV çıktısı:
timestamp, symbol, rsi, macd, adx, ..., label
```

### Görev 7.2: XGBoost Model Eğitimi
```
Gereksinimler:
1. Yukarıdaki feature'ları kullanarak binary classification model eğit
2. Train/test split: %80/%20
3. Hyperparameter tuning (GridSearchCV)
4. Model metriklerini logla (accuracy, precision, recall, F1)

Model Kullanımı:
- Her sinyal üretildiğinde ML modelden prediction al
- Model confidence > %70 -> Sinyali uygula
- Model confidence < %70 -> Sinyali ignore et
```

**Beklenen Çıktı Dosyaları:**
- `src/ml/feature_engineer.py` (yeni)
- `src/ml/model_trainer.py` (yeni)
- `src/ml/predictor.py` (yeni)
- `data/training_data.csv` (çıktı)
- `models/xgboost_model.pkl` (kaydedilmiş model)

---

## UYGULAMA SIRASI VE TESLİM BEKLENTİLERİ

### Hafta 1: Aşama 1 + 2
- Trailing stop, kısmi kar, time-based stop -> Production'da çalışır durumda
- Volatilite bazlı pozisyon boyutlandırma -> Test edilmiş
- Unit testler yazılmış
- README'de kullanım örnekleri eklenmiş

### Hafta 2: Aşama 3 + 4
- Market rejim tespiti -> Canlı veride test edilmiş
- Funding rate entegrasyonu -> En az 3 günlük veri toplanmış
- Dashboard'a yeni metrikler eklenmiş

### Hafta 3-4: Aşama 5 + 6
- Multi-strategy framework -> 3 strateji çalışıyor
- Portfolio limitleri -> Enforce ediliyor
- Backtest sonuçları dokümante edilmiş

### Ay 2+: Aşama 7
- ML pipeline kurulmuş
- En az 1000 trade verisi toplanmış
- Model production'da A/B test ediliyor

---

## KRİTİK NOTLAR

1. **Backward Compatibility:** Her aşamada eski kod çalışmaya devam etmeli. Feature flag'ler kullan.

2. **Logging:** Her yeni özellik için detaylı log ekle. Debug modunda ne olduğu anlaşılmalı.

3. **Config:** Tüm parametreler (ATR multiplier, kar hedefleri, limitler) `.env` veya `config.yaml`'da olmalı.

4. **Error Handling:** Binance API hataları (rate limit, insufficient margin) düzgün handle edilmeli.

5. **Testing:** Her aşama için en az basic unit test yaz. Kritik fonksiyonlar için mock test.

6. **Documentation:** Her yeni modül için docstring ve örnek kullanım ekle.

---

## BAŞARI KRİTERLERİ

Aşama 1 tamamlandığında:
- ✅ Bot artık stop loss ile pozisyonları koruyor
- ✅ Karlar otomatik olarak realize ediliyor
- ✅ Sonsuz beklemeler yok (time-based stop)

Aşama 3 tamamlandığında:
- ✅ Bot ranging marketlerde işlem yapmıyor
- ✅ Volatilite yüksekken risk azaltılmış
- ✅ Sharpe ratio artmış (daha iyi risk/ödül)

Aşama 5 tamamlandığında:
- ✅ Win rate %60+ (multi-strategy konsensüs sayesinde)
- ✅ Max drawdown <%15
- ✅ Portfolio correlation <0.6

---

Bu prompt'u AI asistanınıza verin ve "Aşama 1, Görev 1.1'i uygula" şeklinde adım adım ilerleyin. Her aşamadan sonra test edin, backtest çalıştırın ve sonraki aşamaya geçin.
