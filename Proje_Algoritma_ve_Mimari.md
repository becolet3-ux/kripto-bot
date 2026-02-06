# Kripto Bot Projesi - Algoritma ve Mimari Dokümantasyonu (v2.1)

Bu belge, Kripto Bot projesinin **Binance Global (USDT)** sistem mimarisini, gelişmiş özelliklerini ve operasyonel süreçlerini detaylandırmaktadır. Proje, **USDT** bazlı işlemlere ve çoklu strateji yapısına odaklanmıştır.

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

---

## 2. Gelişmiş Özellikler: Mantık ve Örnekler

Botun sahip olduğu kritik risk yönetimi ve strateji özelliklerinin detaylı çalışma mantığı aşağıdadır.

### 2.1. Funding Rate Strateji Entegrasyonu
Funding Rate (Fonlama Oranı), vadeli işlemler piyasasında pozisyon tutanların birbirine ödediği komisyondur. Piyasa yönü hakkında güçlü sinyaller verir.

*   **Mantık:**
    *   **Veri:** `FundingRateLoader` her 8 saatte bir tüm paritelerin oranlarını çeker.
    *   **Pozitif (>%0.05):** Long pozisyonlar için destekleyici (Boğa piyasası emaresi). Skoru artırır.
    *   **Negatif (<-%0.05):** Short baskısı veya düşüş beklentisi. Long işlemleri **bloklar**.
*   **Örnek Senaryo:**
    *   Bot `BTC/USDT` için AL sinyali üretti (Skor: 7.0).
    *   Ancak Funding Rate `-0.08%` (Negatif).
    *   **Sonuç:** Bot, "Negative Funding" gerekçesiyle bu işlemi **iptal eder** ve pozisyona girmez.

### 2.2. Trailing Stop Loss (İz Süren Stop)
Fiyat lehimize hareket ettiğinde karı korumak için stop seviyesini yukarı taşıyan mekanizmadır.

*   **Mantık:**
    *   **Başlangıç:** Giriş fiyatının %5 altı (veya ATR katı).
    *   **Güncelleme:** Fiyat her yeni zirve yaptığında, stop seviyesi de `(Yeni Zirve - ATR)` seviyesine çekilir. Stop seviyesi asla aşağı inmez.
*   **Örnek Senaryo:**
    *   Giriş: 100$, İlk Stop: 95$.
    *   Fiyat 110$'a çıktı. Yeni Stop: 105$.
    *   Fiyat 108$'a düştü. Stop 105$'da kalır.
    *   Fiyat 104$'a düşerse **STOP OLUR** (5$ kar ile).

### 2.3. Kısmi Kar Realizasyonu (Partial Take Profit)
Pozisyon hedefe gitmeden dönerse elde edilen karın bir kısmını garantiye almak için kullanılır.

*   **Mantık:**
    *   Pozisyon **%4** kara ulaştığında tetiklenir.
    *   Mevcut miktarın **%50'si** o anki fiyattan satılır.
    *   Kalan %50 için Stop Loss seviyesi **Giriş Fiyatına (Breakeven)** çekilir.
*   **Sonuç:** İşlem artık "Risk-Free" (Risksiz) hale gelir. Fiyat giriş seviyesine dönse bile zarar edilmez.

### 2.4. Dinamik Kaldıraç (Dynamic Leverage)
Piyasa volatilitesine göre risk seviyesini otomatik ayarlar.

*   **Mantık:**
    *   `VolatilityCalculator` son 14 mumluk ATR ve değişim oranını ölçer.
    *   **Düşük Volatilite (<%2):** **3x** Kaldıraç (Daha yüksek kar potansiyeli).
    *   **Orta Volatilite (%2-4):** **2x** Kaldıraç (Dengeli).
    *   **Yüksek Volatilite (>%4):** **1x** Kaldıraç (Sadece ana para, risk minimizasyonu).

### 2.5. Portföy Limitleri ve Smart Swap
Sermayeyi korumak ve en iyi fırsatları değerlendirmek için portföy yönetimi yapar.

*   **Limit:** Maksimum **4** açık pozisyon.
*   **Smart Swap (Akıllı Değişim):**
    *   Portföy dolu (4/4) iken çok yüksek skorlu (örn. 8.5/10) yeni bir fırsat gelirse:
    *   Mevcut portföydeki en düşük skorlu (örn. 5.0/10) pozisyonu anında satar.
    *   Yeni ve güçlü olan pozisyonu açar.
    *   Bu sayede sermaye her zaman en "sıcak" fırsatlarda değerlendirilir.

---

## 3. Dashboard ve Metrikler

Dashboard (`src/dashboard.py`), botun hem Canlı (Live) hem de Simülasyon (Paper) modundaki durumunu tek bir arayüzde gösterir.

### 3.1. Live vs Paper Ayrımı
*   Bot `LIVE_TRADING=True` ile çalışıyorsa başlıkta **"CANLI İŞLEM"** yazar.
*   Bot `LIVE_TRADING=False` ile çalışıyorsa başlıkta **"Paper Trading"** yazar.
*   **Önemli:** Live modda, Dashboard Binance cüzdanınızdaki gerçek varlıkları (`wallet_assets`) otomatik algılar ve pozisyon listesinde gösterir.

### 3.2. Kritik Metrikler
*   **Toplam Bakiye (Tahmini):** Cüzdandaki USDT ve coinlerin toplam USDT değeri.
*   **Sanal Nakit:** (Sadece Paper Mod) Kullanılabilir sanal USDT bakiyesi.
*   **Günlük PnL:** O gün içinde yapılan işlemlerden elde edilen Kar/Zarar oranı. **% -5.0** altına düşerse bot o gün için işlem yapmayı durdurur (Circuit Breaker).
*   **Brain Planı:** Botun neden işlem açtığına veya neden beklediğine dair yapay zeka yorumları.

---

## 4. Operasyonel Checklist (Günlük/Haftalık)

Botun sağlıklı çalışması için yapılması gereken kontroller:

### Günlük Kontroller
1.  **Dashboard Kontrolü:**
    *   Bot çalışıyor mu? (Son güncelleme saati güncel mi?)
    *   Hata mesajı var mı? (Kırmızı uyarı kutucukları).
    *   Açık pozisyon sayısı ve PnL durumu normal mi?
2.  **Log Kontrolü:**
    *   `docker-compose logs --tail=100 bot` komutu ile son loglara bakın.
    *   "ERROR" veya "Exception" kelimelerini aratın.

### Haftalık Kontroller
1.  **Sunucu Kaynakları:**
    *   AWS/Sunucu disk ve RAM doluluk oranı (`htop`, `df -h`).
2.  **Güncellemeler:**
    *   Git reposundan güncellemeleri çekin (`git pull`).
    *   Docker imajını yeniden derleyin (`docker-compose up -d --build`).
3.  **Performans Analizi:**
    *   Haftalık PnL durumunu not edin.
    *   Hangi stratejinin (Breakout/Momentum/MeanRev) daha iyi çalıştığını analiz edin.

---

## 5. Troubleshooting (Sorun Giderme)

| Sorun | Olası Neden | Çözüm |
| :--- | :--- | :--- |
| **İşlem Açmıyor** | Bakiye yetersiz, piyasa yatay (regime), veya funding rate negatif. | Dashboard'daki "Brain Planı" sekmesine bakın. "WAIT" veya "Negative Funding" sebebini kontrol edin. |
| **Dashboard Veri Gelmiyor** | Bot durmuş veya State dosyası bozuk. | `docker-compose logs` ile hatayı bulun. Gerekirse `data/bot_state.json` dosyasını silip yeniden başlatın. |
| **API Hatası (401/403)** | API Key süresi dolmuş veya IP izni yok. | Binance panelinden API anahtarını ve IP whitelist ayarlarını kontrol edin. |
| **Sık Stop Oluyor** | Volatilite çok yüksek, stop aralığı dar. | `settings.py` içinde `STOP_LOSS_PCT` değerini artırın veya ATR çarpanını güncelleyin. |

---

## 6. Roadmap (Yol Haritası)

Projenin gelecek vizyonu ve planlanan geliştirmeler:

*   **Faz 1-5 (Tamamlandı):** Temel altyapı, çoklu strateji, risk yönetimi, paper trading, dashboard.
*   **Faz 6 (Q2 2026):** **Machine Learning (ML) Modeli:** Toplanan verilerle eğitilmiş XGBoost/LSTM modelinin karar mekanizmasına dahil edilmesi (Şu an veri toplama modunda).
*   **Faz 7 (Q3 2026):** **Webhook & TradingView Entegrasyonu:** Dış kaynaklı sinyallerin bota entegre edilmesi.
*   **Faz 8 (Q4 2026):** **DeFi & DEX Desteği:** Merkeziyetsiz borsalarda (Uniswap/Pancake) işlem yeteneği.
