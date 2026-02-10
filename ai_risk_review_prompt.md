Bu dosyadaki metni, kendi yapay zekanı (veya kod asistanını) yönlendirmek için PROMPT olarak kullanabilirsin.

---

## GÖREV

Elinde bir kripto alım-satım botu projesi var. Aşağıdaki dosyalarda tespit edilen kritik hataları ve eksikleri **tespit et, doğrula ve düzeltme önerileri üret**:

- `src/execution/executor.py`
- `src/execution/stop_loss_manager.py`
- `src/main.py`
- `src/utils/state_manager.py`
- `config/settings.py`

Öncelik: **risk yönetimi**, **para kaybını sınırlama**, **botun beklenen şekilde trade açıp kapaması**.

Kod stili ve mevcut mimariyi mümkün olduğunca koru; sadece gerekli yerleri düzelt.

---

## 1. Günlük Zarar Limiti (MAX_DAILY_LOSS_PCT) Bug’u

**Sorun tanımı (kritik):**

- `config/settings.py` içinde `MAX_DAILY_LOSS_PCT` şu şekilde tanımlı:
  - `MAX_DAILY_LOSS_PCT: float = 5.0  # Günlük maksimum %5 zarar`
- `src/execution/executor.py` içinde `check_daily_loss_limit` fonksiyonunda:
  - `self.max_daily_loss = settings.MAX_DAILY_LOSS_PCT`
  - `drawdown_pct = (start_balance - current_balance) / start_balance`  → bu değer **0.05** gibi bir orandır.
  - Karşılaştırma şu şekilde yapılıyor:
    - `if drawdown_pct >= self.max_daily_loss:` → örnek: `0.05 >= 5.0` hiçbir zaman true olmaz.

**Sonuç:**

- Günlük equity drawdown limiti fiilen **çalışmıyor**. Kullanıcı 5.0’ı yüzde zannediyor ama kod oran gibi kullanmıyor.

**İSTEK:**

1. Bu davranışı düzelt:
   - Ya `MAX_DAILY_LOSS_PCT` değerini yorumuyla uyumlu hale getir (örn. `0.05`),  
   - Ya da kodda `drawdown_pct` ile karşılaştırma yaparken yüzdeye çevir (örn. `drawdown_pct * 100 >= self.max_daily_loss`).
2. Aynı dosyada `daily_realized_pnl` tabanlı eski kontrol ile yeni equity tabanlı kontrolün **birbiriyle tutarlı** çalışmasını sağla.
3. Değişikliklerden sonra:
   - Değişiklik için kısa bir yorum ekle (neden böyle yaptığını açıklayan).
   - Mantık testine uygun **basit örnekler** düşün (başlangıç 1000, şu an 900 → %10 loss gibi).

---

## 2. Normal ENTRY Sinyallerinin Fiilen Devre Dışı Olması

**Sorun tanımı (çok kritik, fonksiyonel):**

`src/execution/executor.py` içinde `execute_strategy` fonksiyonunda `TradeSignal` akışı şu şekilde:

- `if action == "ENTRY":`
  - Sniper modu (`force_all_in == True`) durumunda:
    - `calculate_quantity(..., force_all_in=True)` çağrılıyor, sonra:
      - `await self.execute_buy(...)`
      - Ardından **`return`** ile fonksiyon tamamen bitiyor (bu kısım mantıklı).
  - Sniper modu **DEĞİLSE**:
    - ENTRY branch’in sonunda **tekrar bir `return`** var ve normal giriş mantığının olduğu blok aşağıda kalıyor.
    - Yani, sniper olmayan ENTRY sinyalleri için:
      - Pozisyon adedi limiti kontrolü (`MAX_OPEN_POSITIONS`)
      - `calculate_quantity` çağrısı
      - `execute_buy`
      - Bunların hiçbiri çalışmıyor; fonksiyon erken `return` ile bitiyor.

**Sonuç:**

- Sniper modu haricinde, bot **hiç yeni pozisyon açmıyor**.  
- Kullanıcı sinyal görüyor ama trade gerçekleşmiyor.

**İSTEK:**

1. `execute_strategy` içindeki ENTRY akışını yeniden düzenle:
   - Sniper modu (`force_all_in`) için erken `return` mantığını koru (mantıklı).
   - Ama normal ENTRY akışı için:
     - Gereksiz/yanlış `return`’leri kaldır veya uygun blok içine taşı.
     - `MAX_OPEN_POSITIONS` kontrolü, risk/ATR/regime bilgisiyle `calculate_quantity`, sonra `execute_buy` çalışmalı.
2. Mantık şu olmalı:
   - Eğer pozisyon yoksa (`not current_pos`) VE pozisyon sayısı limit altında ise:
     - Risk skoruna ve ATR/market regime bilgisine göre miktar hesapla.
     - Miktar > 0 ise, `execute_buy` çağır.
3. Değişiklikten sonra, fonksiyonun `TradeSignal` listesi üzerinde yine düzgün iterate ettiğinden emin ol.

---

## 3. StopLoss / Trailing / Partial Take-Profit Mantığındaki Eksiklikler

**İlgili dosyalar:**

- `src/execution/stop_loss_manager.py`
- `src/execution/executor.py` (`check_risk_conditions`, `execute_buy`, `execute_sell`)

**Sorunlar:**

1. `StopLossManager.check_exit_conditions` içinde:
   - Pozisyondan `trailing_stop_price` okunuyor:
     - `current_stop_price = float(position.get('trailing_stop_price', 0.0))`
   - Fakat `execute_buy` içinde pozisyon sözlüğü şu alanlarla set ediliyor:
     - `'stop_loss'`, `'highest_price'`, `'atr_value'`, `'features'`, `'is_sniper_mode'`
   - Yani `trailing_stop_price` **hiç set edilmiyor**, ama `stop_loss` alanı set ediliyor.
   - Bu tutarsızlık, trailing stop’un beklendiği gibi çalışmamasına yol açıyor.

2. `partial_exit_executed` bayrağı:
   - `StopLossManager.check_exit_conditions` içinde bu bayrak okunuyor:
     - `if not position.get('partial_exit_executed', False): ...`
   - Ancak hiçbir yerde (örneğin `execute_sell` içinde) `partial_exit_executed` pozisyona yazılmıyor.
   - Sonuç olarak aynı pozisyona birden fazla `PARTIAL_CLOSE` sinyali gelebilir; pratikte miktar azalsa da davranış **belirsiz**.

3. Trailing mantığı:
   - ATR hesaplanıyor, `stop_distance = atr_value * multiplier`.
   - `final_stop_price` güncellendiğinde sonuç dict’inde `new_stop_price` dönülüyor.
   - `executor.check_risk_conditions` içinde, bu `new_stop_price` sadece `position['stop_loss']` içine yazılıyor, `trailing_stop_price` kullanılmıyor.

**İSTEK:**

1. `stop_loss` / `trailing_stop_price` isimlendirmesini ve kullanımını **tutarlı** hale getir:
   - Ya sadece bir alan kullan (örneğin `stop_loss`) ve her yerde bunu oku/yaz.
   - Ya da gerçekten iki ayrımı (sabit SL vs trailing SL) net ayır ve doğru set et.
2. `partial_exit_executed` bayrağını:
   - `PARTIAL_CLOSE` işlemi başarıyla uygulandığında `paper_positions[symbol]` içine yaz:
     - Örn: `position['partial_exit_executed'] = True`.
   - Böylece aynı parti için birden fazla partial exit tetiklenmesin (veya bu davranış kasıtlıysa, dokümante et).
3. Trailing stop mantığının beklenen davranışı:
   - Fiyat yükseldikçe stop yukarı çekilsin, ama aşağı inmesin.
   - Fiyat stop’un altına inerse pozisyon `CLOSE` olsun.
   - Mevcut kod bu mantığa yakın; sadece field adları ve state kaydı netleştirilmeli.

---

## 4. State Dosyası Yapısı ve Atomik Yazım Eksikliği

**İlgili dosya:**

- `src/utils/state_manager.py`
- Ayrıca `src/execution/executor.py` içindeki `save_positions`, `close`, `update_commentary` vs.

**Sorunlar:**

1. State yapısı:
   - `Executor.__init__` içinde:
     - `self.full_state = loaded_state if loaded_state else {'paper_positions': {}, 'wallet_assets': {}, 'total_balance': 0.0}`
   - `save_positions` içinde:
     - `self.state_manager.save_state(self.full_state)` çağrılıyor (doğru).
   - Ancak `Executor.close` içinde:
     - `self.state_manager.save_state(self.paper_positions)` gibi bir çağrı var ise (veya benzeri bir yerde sadece `paper_positions` dict’i gönderiliyorsa), state dosyası beklenen şemadan sapabilir.
   - Bu, yeniden başlatma sonrası state migration vb. için **potansiyel bozulma** yaratır.

2. Atomik yazım yok:
   - `StateManager.save_state` ve `save_stats` direkt:
     - `with open(self.filepath, 'w') as f: json.dump(...)`
   - Eğer process çökmesi / disk sorunu vb. olursa, JSON dosyası **bozuk** kalabilir.

**İSTEK:**

1. `Executor` tarafında:
   - State dosyasını yazarken **sadece `self.full_state`** kullan.
   - `save_state(self.paper_positions)` gibi, schema bozan çağrılar varsa düzelt.
2. `StateManager` tarafında:
   - Atomik yazım uygula:
     - Örnek yaklaşım:
       - `tmp_path = self.filepath + ".tmp"`
       - Önce `tmp_path`’e yaz.
       - Sonra `os.replace(tmp_path, self.filepath)` ile atomik olarak değiştir.
   - Aynısını `save_stats` için de uygula.

---

## 5. Sniper Modu Riskleri ve İyileştirme Önerisi

**Durum:**

- Sniper modunda (`force_all_in == True`):
  - `calculate_quantity` içinde:
    - `target_position_size_usdt = free_balance * current_leverage * 0.98`
  - Yani **serbest bakiyenin neredeyse tamamı**, kaldıraçla birlikte tek pozisyona giriyor.
- Günlük zarar limiti bug’u düzeltmeden önce bu davranış **aşırı riskli**.

**İSTEK:**

1. Günlük zarar limiti düzeltildikten sonra bile, sniper modunun:
   - Belki ayrı bir `SNIPER_MAX_RISK_PCT` veya `SNIPER_MAX_NOTIONAL_MULTIPLIER` gibi ayarla sınırlandırılmasını değerlendir.
   - En azından dokümantasyon ve log’larda çok net bir uyarı mesajı ver:
     - Örneğin: “Sniper Mode: Tüm bakiye ile tek pozisyon – yüksek risk.”
2. Eğer mümkünse:
   - Sniper modunu da günlük zarar limiti ve `EMERGENCY_SHUTDOWN_ENABLED` ile uyumlu olacak şekilde güvenli tut.

---

## BEKLENEN ÇIKTI

Bu prompt’u işledikten sonra, yapman gerekenler:

1. İlgili dosyaları (`executor.py`, `stop_loss_manager.py`, `state_manager.py`, `settings.py`, `main.py`) sırayla gözden geçir.
2. Yukarıda tanımlanan her bir sorun için:
   - Sorunun kod içindeki yerini **doğrula** (satır/alan bazında).
   - En az müdahale ile, ama sağlam bir şekilde **düzeltici değişiklikler** öner.
3. Önerdiğin değişiklikler için:
   - Kısa açıklama yaz (neden böyle yaptın, önceki davranış neydi, şimdi ne olacak).
   - Mümkünse basit “senaryo örnekleri” ile mantığı test et (sözlü olarak).
4. En sonda, yaptığın düzeltmelerden sonra:
   - Botun risk profili,
   - Günlük zarar limiti davranışı,
   - Normal ENTRY sinyallerinin çalışması,
   - Stop-loss / trailing / partial exit davranışı
   için kısa bir **özet rapor** çıkar.

