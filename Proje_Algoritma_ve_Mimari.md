# Kripto Bot Projesi - Algoritma ve Mimari Dokümantasyonu (v2.2)

Bu belge, Kripto Bot projesinin **Binance Global (USDT)** sistem mimarisini, gelişmiş özelliklerini ve operasyonel süreçlerini detaylandırmaktadır. Proje, **USDT** bazlı işlemlere, çoklu strateji yapısına ve düşük bakiye (Sniper Mode) yönetimine odaklanmıştır.

> **Not:** v2.2 itibarıyla Paper Trading modu devre dışı bırakılmış ve sadece **LIVE (Canlı)** mod aktiftir.

## 1. Sistem Mimarisi (Global - USDT Focused)

Sistem; veri toplama, analiz, karar destek (beyin), yürütme ve izleme katmanlarından oluşan modüler bir yapıya sahiptir.

```mermaid
graph TD
    subgraph Data Layer
        A1[Binance Global Loader (CCXT)]
        A2[Funding Rate Loader]
        A3[Sentiment Analyzer]
    end
    
    subgraph Analysis Layer
        B1[Market Analyzer Technical]
        B2[Multi-Timeframe Analysis]
        B3[Sentiment Score]
        B4[Advanced Indicators]
        B5[Market Regime Detector]
    end
    
    subgraph Decision Layer
        C1[Multi-Strategy Manager (Phase 5)]
        C2[Voting System]
        C3[Safety Checks & Risk Manager]
        C4[Regime Adaptive Strategy]
    end
    
    subgraph Execution Layer
        D1[Executor (Global/USDT)]
        D4[Wallet & Asset Manager]
        D5[Position Sizer (Volatility Based)]
        D6[Sniper Mode (Low Balance)]
    end
    
    subgraph Infrastructure Layer
        I1[Docker Containerization]
        I2[AWS EC2 Cloud]
        I3[Advanced Dashboard (USDT)]
    end
    
    A1 & A2 --> B1 & B2 & B4 & B5
    A3 --> B3
    B1 & B2 & B3 & B4 & B5 --> C1
    C1 --> C2 --> C3 --> C4 --> D1
    C3 --> D1
    D1 --> D5 --> D4
    D4 --> D6
    D1 --> I3
```

---

## 2. Gelişmiş Özellikler: Mantık ve Örnekler

Botun sahip olduğu kritik risk yönetimi, strateji ve bakiye yönetimi özelliklerinin detaylı çalışma mantığı aşağıdadır.

### 2.1. Sniper Modu ve Dust (Toz) Yönetimi (YENİ)
Düşük bakiyelerde (<50$) botun verimliliğini korumak ve "bakiye erimesi" sorununu önlemek için geliştirilmiş özel bir moddur.

*   **Sniper Modu:**
    *   Toplam bakiye **50 USDT** altına düştüğünde otomatik aktifleşir.
    *   Mevcut tüm pozisyonları satıp nakite geçmeye odaklanır.
    *   Tek bir "En İyi" sinyale tüm bakiye (All-In) ile girer.
*   **Dust (Toz) Temizliği:**
    *   Değeri **6 USDT** (veya 10 USDT) altında kalan ve satılamayan (Binance min. işlem limiti altı) "toz" varlıkları algılar.
    *   Bu varlıkları otomatik olarak **BNB'ye dönüştürür** (`convert_dust_to_bnb`).
    *   Böylece küçük bakiyelerin cüzdanda atıl kalması ve swap döngüsüne girmesi engellenir.
*   **0.0 Fiyat Koruması:**
    *   Satış sırasında API'den fiyat `0.0` dönerse, anlık fiyat tekrar sorgulanır.
    *   Hatalı fiyatla satış yapılması ve bakiyenin yanlış hesaplanması engellenir.

### 2.2. Funding Rate Strateji Entegrasyonu
Funding Rate (Fonlama Oranı), vadeli işlemler piyasasında pozisyon tutanların birbirine ödediği komisyondur. Piyasa yönü hakkında güçlü sinyaller verir.

*   **Mantık:**
    *   **Veri:** `FundingRateLoader` her 8 saatte bir tüm paritelerin oranlarını çeker.
    *   **Pozitif (>%0.05):** Long pozisyonlar için destekleyici (Boğa piyasası emaresi). Skoru artırır.
    *   **Negatif (<-%0.05):** Short baskısı veya düşüş beklentisi. Long işlemleri **bloklar**.

### 2.3. Trailing Stop Loss (İz Süren Stop)
Fiyat lehimize hareket ettiğinde karı korumak için stop seviyesini yukarı taşıyan mekanizmadır.

*   **Mantık:**
    *   **Başlangıç:** Giriş fiyatının %5 altı (veya ATR katı).
    *   **Güncelleme:** Fiyat her yeni zirve yaptığında, stop seviyesi de `(Yeni Zirve - ATR)` seviyesine çekilir.
    *   Stop seviyesi asla aşağı inmez.

### 2.4. Kısmi Kar Realizasyonu (Partial Take Profit)
Pozisyon hedefe gitmeden dönerse elde edilen karın bir kısmını garantiye almak için kullanılır.

*   **Mantık:**
    *   Pozisyon **%4** kara ulaştığında tetiklenir.
    *   Mevcut miktarın **%50'si** o anki fiyattan satılır.
    *   Kalan %50 için Stop Loss seviyesi **Giriş Fiyatına (Breakeven)** çekilir.

### 2.5. Portföy Limitleri ve Smart Swap
Sermayeyi korumak ve en iyi fırsatları değerlendirmek için portföy yönetimi yapar.

*   **Limit:** Maksimum **4** açık pozisyon.
*   **Smart Swap (Akıllı Değişim):**
    *   Portföy dolu (4/4) iken çok yüksek skorlu (örn. 8.5/10) yeni bir fırsat gelirse:
    *   Mevcut portföydeki en düşük skorlu pozisyonu satar.
    *   **Dust Kontrolü:** Satış sonrası kalan bakiye "toz" ise BNB'ye çevrilir ve hafızadan silinir.
    *   Yeni ve güçlü olan pozisyon açılır.

---

## 3. Dashboard ve Metrikler

Dashboard (`src/dashboard.py`), botun **Canlı (Live)** durumunu gösterir. Paper trading modu kaldırılmıştır.

### 3.1. Kritik Metrikler
*   **Toplam Bakiye (USDT):** Cüzdandaki USDT ve coinlerin toplam USDT değeri.
*   **Günlük PnL:** O gün içinde yapılan işlemlerden elde edilen Kar/Zarar oranı. **% -5.0** altına düşerse bot o gün için işlem yapmayı durdurur (Circuit Breaker).
*   **Brain Planı:** Botun neden işlem açtığına veya neden beklediğine dair yapay zeka yorumları.
*   **Market Rejimi:** Piyasanın Yönü (TREND/SIDEWAYS) ve Volatilitesi.

---

## 4. Operasyonel Checklist (Günlük/Haftalık)

Botun sağlıklı çalışması için yapılması gereken kontroller:

### Günlük Kontroller
1.  **Dashboard Kontrolü:**
    *   Bot çalışıyor mu? (Son güncelleme saati güncel mi?)
    *   **Bakiye Kontrolü:** Beklenmedik düşüş var mı? (Varsa "Dust Loop" kontrolü yapın).
2.  **Log Kontrolü:**
    *   `docker-compose logs --tail=100 bot` komutu ile son loglara bakın.
    *   "ERROR", "Exception" veya "Dust" kelimelerini aratın.

### Haftalık Kontroller
1.  **Sunucu Kaynakları:**
    *   AWS/Sunucu disk ve RAM doluluk oranı (`htop`, `df -h`).
2.  **Güncellemeler:**
    *   Git reposundan güncellemeleri çekin (`git pull`).
    *   Docker imajını yeniden derleyin (`docker-compose up -d --build`).

---

## 5. Troubleshooting (Sorun Giderme)

| Sorun | Olası Neden | Çözüm |
| :--- | :--- | :--- |
| **Bakiye Eriyor / Azalıyor** | "Dust Loop" sorunu. Bot küçük bakiyeleri satamayıp komisyon ödüyor olabilir. | **v2.2 ile Çözüldü:** Bot artık <6$ bakiyeleri otomatik BNB'ye çeviriyor. Loglarda "Dust Convert" arayın. |
| **İşlem Açmıyor** | Bakiye yetersiz, piyasa yatay (regime), veya funding rate negatif. | Dashboard'daki "Brain Planı" sekmesine bakın. "WAIT" veya "Negative Funding" sebebini kontrol edin. |
| **Dashboard Veri Gelmiyor** | Bot durmuş veya State dosyası bozuk. | `docker-compose logs` ile hatayı bulun. Gerekirse `data/bot_state.json` dosyasını silip yeniden başlatın. |
| **API Hatası (401/403)** | API Key süresi dolmuş veya IP izni yok. | Binance panelinden API anahtarını ve IP whitelist ayarlarını kontrol edin. |

---

## 6. Roadmap (Yol Haritası)

Projenin gelecek vizyonu ve planlanan geliştirmeler:

*   **Faz 1-5 (Tamamlandı):** Temel altyapı, çoklu strateji, risk yönetimi, dashboard.
*   **Faz 6 (Q2 2026):** **Machine Learning (ML) Modeli:** Toplanan verilerle eğitilmiş XGBoost/LSTM modelinin karar mekanizmasına dahil edilmesi (Şu an veri toplama modunda).
*   **Faz 7 (Q3 2026):** **Webhook & TradingView Entegrasyonu:** Dış kaynaklı sinyallerin bota entegre edilmesi.
*   **Faz 8 (Q4 2026):** **DeFi & DEX Desteği:** Merkeziyetsiz borsalarda (Uniswap/Pancake) işlem yeteneği.

---

## 7. Teknik Altyapı Detayları (Technical Infrastructure)

*   **Programlama Dili:** Python 3.9+
*   **Temel Kütüphaneler:**
    *   `ccxt`: Binance Global ve TR borsa bağlantısı ve emir yönetimi için.
    *   `pandas` & `numpy`: Zaman serisi analizi, indikatör hesaplamaları ve veri manipülasyonu için.
    *   `ta-lib`: RSI, MACD, Bollinger Bands gibi teknik indikatörlerin performanslı hesaplanması için.
    *   `asyncio`: Eşzamanlı (concurrent) veri tarama ve emir yönetimi için asenkron mimari.
*   **Veritabanı Yapısı:**
    *   Proje, karmaşıklığı azaltmak ve taşınabilirliği artırmak için **Dosya Tabanlı (File-Based)** bir yapı kullanır.
    *   `bot_state.json`: Canlı botun anlık durumu, pozisyonları ve bakiyesi.
    *   `bot_brain.json`: Beyin sisteminin öğrenilmiş ağırlıkları ve geçmiş işlem istatistikleri.
    *   Herhangi bir harici SQL/NoSQL veritabanı gerektirmez, bu da kurulumu ve yedeklemeyi kolaylaştırır.
*   **Mimari:** Modüler "Micro-Service Like" yapı. Executor (Yürütücü), Strategy (Karar), Risk (Denetim) ve Brain (Yönetim) modülleri birbirinden bağımsız çalışır ancak uyum içindedir.

## 8. Strateji Detayları (Strategy Deep Dive)

Bot, tek bir indikatöre güvenmek yerine "Weighted Voting" (Ağırlıklı Oylama) sistemi kullanır. Karar vermek için toplam konsensüsün **%55** (0.55) üzerinde olması gerekir.

### Kullanılan Alt Stratejiler:
1.  **Breakout Strategy (Ağırlık: 0.4):**
    *   **Mantık:** Fiyatın sıkışma alanından (Bollinger Squeeze) hacimli bir şekilde çıkmasını hedefler.
    *   **İndikatörler:** Bollinger Band Width (Bant Genişliği), Volume Ratio (Hacim Oranı > 2x), Üst Bant Kırılımı.
    *   **Giriş:** Bant genişliyor + Fiyat üst bandı kırıyor + Hacim ortalamanın 2 katı.
2.  **Mean Reversion Strategy (Ağırlık: 0.3):**
    *   **Mantık:** Aşırı satım (Oversold) bölgelerinden tepki yükselişlerini yakalar.
    *   **İndikatörler:** RSI (< 35), Bollinger Lower Band (Alt Bant Teması), MACD Histogram.
    *   **Giriş:** Fiyat alt banda değdi + RSI 35 altından yukarı dönüyor + MACD histogramı dip yapıp yükselişe geçti.
3.  **Momentum Strategy (Ağırlık: 0.3):**
    *   **Mantık:** Güçlü trendleri takip eder. "Trend is your friend" ilkesi.
    *   **İndikatörler:** ADX (Trend Gücü), SuperTrend, MACD.
    *   **Giriş:** ADX > 25 (Güçlü Trend) + SuperTrend Boğa (Bullish) + MACD Al Sinyali.

**Zaman Dilimleri:**
*   **Sinyal:** 15 Dakika (Hızlı tepki için).
*   **Trend/Rejim Teyidi:** 1 Saat (Ana yönü belirlemek için).

## 9. Risk Yönetimi (Risk Management Details)

Sermaye koruması, kar etmekten daha önceliklidir.

*   **Pozisyon Büyüklüğü (Position Sizing):** Sabit miktar yerine **Volatilite Bazlı (ATR)** hesaplama yapılır.
    *   Düşük Volatilite -> Daha Büyük Pozisyon (Daha az risk).
    *   Yüksek Volatilite -> Daha Küçük Pozisyon (Patlama riskine karşı koruma).
*   **Stop Loss:** ATR Trailing Stop (İz Süren Stop). Fiyatla birlikte yukarı hareket eder, asla aşağı inmez.
*   **Circuit Breaker (Sigorta):**
    *   **API Hataları:** Üst üste 5 API hatası alınırsa bot 5 dakika kendini "Soğumaya" alır.
    *   **Günlük Zarar Limiti:** Günlük PnL %-5'in altına düşerse, o gün için yeni işlem açılması durdurulur (Ertesi gün 00:00 UTC'de sıfırlanır).
*   **Sniper Mode:** Toplam varlık kritik seviyenin (100 USDT) altına düşerse, tüm strateji kuralları "Kurtarma Modu"na geçer ve en iyi tek bir işleme odaklanır.

## 10. Brain Sistemi (Brain System Logic)

*   **Yapay Zeka Türü:** Rule-Based (Kural Tabanlı) ve Adaptive (Uyarlanabilir). Şu aşamada LLM (Large Language Model) entegrasyonu yoktur, deterministik algoritmalar çalışır.
*   **İşlevi:**
    *   Her işlemin sonucunu (`WIN` veya `LOSS`) kaydeder.
    *   Başarılı olan stratejinin (örn. Breakout) ağırlığını artırır, başarısız olanınkini azaltır.
    *   Piyasa rejimine (Trending/Ranging) göre hangi stratejinin daha aktif olacağına karar verir.
*   **Öğrenme:** `bot_brain.json` dosyasında strateji performanslarını tutar ve zamanla kendi parametrelerini optimize eder.

## 11. Operasyonel Sorular (Operational FAQ)

*   **Döngü Hızı:** Bot, semboller arasında **0.1 saniye** (100ms) bekleme süresi ile tarama yapar. Bu, Binance API limitlerine (1200 request/dk) takılmadan maksimum hızda tarama sağlar.
*   **Sunucu:** AWS üzerinde Docker konteynerleri içinde çalışır. Canlı (Live) bot, izole bir ortamda çalışarak dış etkenlerden korunur.
*   **Yedekleme:** State dosyaları JSON formatında olduğu için sunucu kapansa bile son durum (pozisyonlar, bakiye) kaybolmaz. Başlangıçta bu dosya okunarak kaldığı yerden devam eder.

## 12. Sorun Alanları ve Çözümleri (Known Issues)

*   **WIF Bakiyesi (Balance Discrepancy):** Cüzdan senkronizasyonunda nadiren görülen "Earn" cüzdanı ile "Spot" cüzdanı arasındaki bakiye farkı. (Çözüm: `sync_wallet` fonksiyonu her döngüde bakiyeyi tazeler).
*   **Dust Accumulation (Toz Birikmesi):** Küçük bakiyelerin işlem limitlerine takılması. (Çözüm: Sniper Modu içindeki `convert_dust_to_bnb` fonksiyonu ile çözüldü).
*   **API Rate Limits:** Çok sık istek atılması sonucu IP ban riski. (Çözüm: Semboller arası `sleep(0.1)` ve hata durumunda `CircuitBreaker` beklemesi ile tamamen önlendi).
