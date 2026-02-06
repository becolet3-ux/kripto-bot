# Kripto Bot Projesi - Algoritma ve Mimari Dokümantasyonu (v2.0)

Bu belge, Kripto Bot projesinin güncellenmiş **Binance Global (USDT)** sistem mimarisini ve algoritma akışını açıklamaktadır. Proje, önceki versiyonlardaki Binance TR (Spot) desteğini devre dışı bırakarak tamamen **Binance Global (Futures/Spot)** altyapısına ve **USDT** bazlı işlemlere odaklanmıştır.

## 1. Sistem Mimarisi (Global - USDT Focused)

Sistem, veri toplama, çok boyutlu analiz, karar verme (beyin), yürütme ve gelişmiş izleme olmak üzere beş ana katmandan oluşur.

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
        D2[Paper Trading Engine]
        D3[Futures Execution]
        D4[Wallet & Asset Manager]
        D5[Position Sizer (Volatility Based)]
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
    D1 --> D5 --> D2 & D3
    D2 & D3 --> D4
    D1 --> I3
```

### Yeni ve Güncellenen Bileşenler (v2.0)

1.  **Global & USDT Odaklı Yapı:**
    *   **Exchange:** Binance Global (`ccxt` kütüphanesi ile).
    *   **Base Currency:** Tamamen **USDT** (Tether) tabanlı.
    *   **Semboller:** `BTC/USDT`, `ETH/USDT` vb.
    *   **TR Desteği:** Kaldırıldı/Devre dışı bırakıldı.

2.  **Multi-Strategy Framework (Phase 5):**
    *   **Strategy Manager:** 3 farklı alt stratejiyi yönetir ve oylama sistemiyle (Weighted Voting) final sinyali üretir.
    *   **Alt Stratejiler:**
        *   **BREAKOUT (Weight 0.4):** Bollinger Band sıkışması sonrası kırılım ve hacim artışı.
        *   **MOMENTUM (Weight 0.3):** Güçlü trend (ADX), SuperTrend ve MACD Golden Cross.
        *   **MEAN REVERSION (Weight 0.3):** RSI < 30 (Oversold), Alt Bollinger Band tepkisi ve MACD dönüşü.
    *   **Consensus:** Toplam oyların %60'ı "ENTRY" derse işlem açılır.

3.  **Paper Trading (Simülasyon) Modu:**
    *   **Sanal Bakiye:** 10.000 USDT (Ayarlanabilir).
    *   **Takip:** Gerçek borsa verileriyle sanal alım-satım yapar.
    *   **Dashboard:** "Sanal Nakit" ve "Toplam Varlık" (USDT) olarak ayrı bir sekmede/bölümde takip edilir.
    *   **Risk:** Sıfır risk ile strateji testi imkanı.

4.  **Risk Management & Sizing:**
    *   **Volatility Based Position Sizing:** ATR ve volatiliteye göre dinamik pozisyon büyüklüğü.
    *   **Min İşlem Limiti:** 6.0 USDT.
    *   **Stop Loss:** ATR tabanlı dinamik stop loss.

## 2. Algoritma Akışı

Botun karar mekanizması artık **Global Mod** ve **Strateji Oylaması** üzerine kuruludur:

### Adım 1: Başlatma
*   **Ayarlar:** `IS_TR_BINANCE=False`, `PAPER_TRADING_BALANCE=10000.0` (USDT).
*   **Bağlantı:** Binance Global API'ye bağlanır (veya Paper Trading için Public API).
*   **Semboller:** USDT çiftlerini (örn. BTC/USDT) otomatik tarar.

### Adım 2: Analiz ve Oylama
*   **Veri:** 1 saatlik mum verileri ve Funding Rate çekilir.
*   **Strateji Oylaması:**
    *   Breakout, Momentum ve Mean Reversion stratejileri ayrı ayrı sinyal üretir.
    *   Ağırlıklı ortalama hesaplanır.
    *   Skor > 0.60 ise **ALIM** sinyali oluşur.
*   **Rejim Kontrolü:** Piyasa rejimi (Trend/Yatay) tespit edilir ve risk parametreleri ayarlanır.

### Adım 3: Yürütme (Execution)
*   **Mod Kontrolü:** 
    *   **Live:** Gerçek emir gönderir (`create_order`).
    *   **Paper:** Sanal bakiyeden düşer, `paper_positions` listesine ekler.
*   **Alım (Long):** Market emri ile giriş yapılır.
*   **Satım (Exit):** Kar al veya Stop Loss seviyelerinde pozisyon kapatılır.
*   **İzleme:** Dashboard üzerinden anlık PnL ve bakiye USDT olarak izlenir.

## 3. Kurulum ve Çalıştırma

### Gereksinimler
*   Docker & Docker Compose
*   Binance Global API Anahtarları (Live Mod için)
*   `.env` dosyası

### Komutlar
*   **Botu Başlat:** `docker-compose up -d --build`
*   **Logları İzle:** `docker-compose logs -f bot`
*   **Durdur:** `docker-compose down`
