# Kripto Bot Projesi - Algoritma ve Mimari Dokümantasyonu (v1.7)

Bu belge, Kripto Bot projesinin güncellenmiş sistem mimarisini, algoritma akışını ve eklenen **Binance Global Futures** ile **AWS Cloud** entegrasyonlarını detaylı bir şekilde açıklamaktadır. Sistem, hem Spot (TR) hem de Vadeli İşlemler (Global) modlarında çalışabilen hibrit bir yapıya kavuşmuştur.

## 1. Sistem Mimarisi (Hybrid Architecture)

Sistem, veri toplama, çok boyutlu analiz, karar verme (beyin), yürütme ve gelişmiş izleme olmak üzere beş ana katmandan oluşur.

```mermaid
graph TD
    subgraph Data Layer
        A1[Binance Global Loader (CCXT)]
        A2[Binance TR Loader (Custom)]
        A3[Sentiment Analyzer]
    end
    
    subgraph Analysis Layer
        B1[Market Analyzer Technical]
        B2[Multi-Timeframe Analysis]
        B3[Sentiment Score]
        B4[Advanced Indicators]
    end
    
    subgraph Decision Layer
        C1[Bot Brain Learning]
        C2[Dynamic Weighting System]
        C3[Safety Checks & Risk Manager]
    end
    
    subgraph Execution Layer
        D1[Executor (Hybrid)]
        D2[Spot Execution (TR)]
        D3[Futures Execution (Global)]
        D4[Wallet & Asset Manager]
    end
    
    subgraph Infrastructure Layer
        I1[Docker Containerization]
        I2[AWS EC2 Cloud]
        I3[Advanced Dashboard]
    end

    A1 & A2 --> B1 & B2 & B4
    A3 --> B3
    B1 & B2 & B3 & B4 --> C1
    C1 --> C2 --> C3 --> D1
    C3 --> D1
    D1 --> D2 & D3
    D2 & D3 --> D4
    D1 --> I3
```

### Yeni ve Güncellenen Bileşenler (v1.7)

1.  **Infrastructure Layer (Altyapı Katmanı):**
    *   **AWS Cloud Integration:** Bot artık AWS EC2 üzerinde, Docker konteynerleri içinde 7/24 çalışmaktadır.
    *   **Dockerization:** `kripto-bot-core` ve `kripto-bot-dashboard` olmak üzere iki ayrı servis olarak yapılandırılmıştır.
    *   **Swap Memory:** Düşük RAM'li sunucularda (t2.micro) OOM hatalarını önlemek için Swap alanı yapılandırılmıştır.

2.  **Execution Layer (Yürütme Katmanı):**
    *   **Hybrid Executor:** `src/execution/executor.py` artık hem Binance TR (Spot) hem de Binance Global (Futures) modlarını destekler.
    *   **Futures Support:** Kaldıraçlı işlemler (Leverage 2x), Short/Long pozisyon mantığı ve USDT teminat yönetimi eklendi.
    *   **Dynamic Limits:** 
        *   **Spot (TR):** Min işlem limiti 40 TRY.
        *   **Futures (Global):** Min işlem limiti 6.0 USDT.

3.  **Data Layer (Veri Katmanı):**
    *   **CCXT Integration:** Binance Global verileri için `ccxt` kütüphanesi entegre edildi.
    *   **Dynamic Symbol Loading:** Bot, çalıştırıldığı moda göre (TR veya Global) taranacak sembolleri (TRY veya USDT çiftleri) otomatik belirler.

## 2. Güncellenmiş Algoritma Akışı

Botun karar mekanizması artık **Mod Bazlı (Mode-Based)** çalışmaktadır:

### Adım 1: Mod Tespiti ve Başlatma
*   **Env Kontrolü:** `.env` dosyasındaki `IS_TR_BINANCE` ve `TRADING_MODE` değişkenlerine göre bot kimliğini belirler.
*   **Global Futures:** `IS_TR_BINANCE=False` ise Global moduna geçer, kaldıraç ayarlarını (2x) yapar ve USDT çiftlerini tarar.
*   **TR Spot:** `IS_TR_BINANCE=True` ise TR moduna geçer, TRY çiftlerini tarar.

### Adım 2: Sinyal ve Risk Yönetimi
*   **Gelişmiş Teknik Analiz:** SuperTrend, CCI, ADX, MFI, VWAP ve Formasyonlar hesaplanır.
*   **Volume Profile:** Fiyatın değer bölgesinde (Value Area) olup olmadığı analiz edilir.
*   **Futures Risk Yönetimi:** 
    *   **ReduceOnly:** Satış emirleri, sadece pozisyon kapatmak için (ReduceOnly=True) gönderilir.
    *   **Margin Check:** Yetersiz teminat durumunda işlem açılmaz.

### Adım 3: Yürütme (Execution)
*   **Alım (Long):** 
    *   Global: `market buy` emri ile Long pozisyon açılır.
    *   TR: `limit buy` veya `market buy` ile coin alınır.
*   **Satım (Close/Short):**
    *   Global: Mevcut Long pozisyonu kapatmak için ters yönde (Sell) işlem yapılır.
    *   TR: Eldeki coin TRY'ye dönüştürülür.
*   **Toz (Dust) Yönetimi:** Min işlem limitinin (40 TRY / 6 USDT) altında kalan "toz" bakiyeler, işlem kilitlenmesini önlemek için kağıt üzerinde (paper_positions) silinir ancak cüzdanda tutulur.

## 3. Bot Brain: Karar Mekanizması

Botun "Beyni" (`brain.py`), geçmiş işlem sonuçlarına göre strateji ağırlıklarını dinamik olarak günceller.

### 3.1. Kullanılan İndikatörler
1.  **Trend:** SuperTrend, SMA, EMA, MACD, ADX.
2.  **Momentum:** RSI, StochRSI, CCI, MFI.
3.  **Volatilite:** Bollinger Bands, ATR, VWAP.
4.  **Market Structure:** Volume Profile (POC, VAH, VAL), Order Book Imbalance.

## 4. Gelişmiş Risk Yönetimi (v1.7)

### 4.1. Portfolio Optimizer
*   **Korelasyon Analizi:** Portföydeki varlıkların birbirine olan bağımlılığı ölçülür. Yüksek korelasyonlu varlıkların aynı anda alınması engellenir.

### 4.2. Güvenlik Mekanizmaları
*   **Geo-Block Protection:** AWS sunucusu Avrupa bölgesinde (Frankfurt/Ireland) konumlandırılarak Binance erişim engeli aşılmıştır.
*   **Circuit Breaker:** Üst üste hata alınması durumunda (API ban riski), bot kendini geçici olarak duraklatır.
*   **Emergency Stop:** Günlük %5 zarar durumunda bot otomatik olarak tüm işlemleri durdurur.

## 5. Teknik İyileştirmeler (v1.7)

*   **Pydantic V2:** Konfigürasyon yönetimi `pydantic-settings` ile modernize edildi.
*   **Docker & Cloud:** Tamamen konteynerize edilmiş yapı ile her ortamda (Local, VPS, Cloud) sorunsuz çalışma.
*   **Dashboard USDT Support:** Dashboard artık Global modda USDT bazlı raporlama yapabilmektedir.
