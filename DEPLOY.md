# 🚀 Kripto Bot Kurulum ve Dağıtım Rehberi

Bilgisayarınızın sürekli açık kalmasına gerek kalmadan, botunuzu 7/24 çalışır halde tutmak için aşağıdaki yöntemleri kullanabilirsiniz.

---

## 💰 Seçenek 1: Ücretli VPS (En Kolay ve Stabil)
Aylık 5-10$ maliyetle en sorunsuz yöntemdir. (DigitalOcean, Hetzner, vb.)
*Kurulum adımları dosyanın en altında mevcuttur.*

---

## 🆓 Seçenek 2: Tamamen Ücretsiz Yöntemler

Sürekli açık bir sunucu için "Sonsuza Kadar Ücretsiz" (Always Free) paketleri olan bulut sağlayıcıları kullanabilirsiniz. Kurulum biraz daha teknik bilgi gerektirebilir ancak **ücretsizdir**.

### A. Google Cloud Platform (GCP) - Always Free
Google, belirli bölgelerde (us-west1, us-central1) **e2-micro** sunucusunu ücretsiz verir.
1.  [Google Cloud Free Tier](https://cloud.google.com/free) sayfasına gidin ve kaydolun (Kredi kartı doğrulama için gereklidir, para çekilmez).
2.  **Compute Engine** > **VM Instances** sayfasına gidin.
3.  **Create Instance** deyin:
    -   **Region:** `us-central1` veya `us-west1` seçin (Önemli!).
    -   **Machine Type:** `e2-micro` (2 vCPU, 1 GB RAM) seçin.
    -   **Boot Disk:** "Change" diyip `Ubuntu 22.04 LTS` seçin ve disk boyutunu `30 GB` (Standart Persistent Disk) yapın.
4.  Oluşturduktan sonra "SSH" butonuna basarak bağlanın ve alttaki kurulum komutlarını uygulayın.

### B. Oracle Cloud Free Tier (En Güçlüsü)
Oracle, çok cömert bir ücretsiz paket sunar (4 vCPU, 24 GB RAM ARM sunucu).
1.  [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) sayfasına kaydolun.
2.  **VM Standard.A1.Flex** (ARM işlemci) seçerek bir sunucu oluşturun.
3.  Ubuntu işletim sistemini seçin.
4.  SSH ile bağlanıp kurulumu yapın.
    *Not: ARM işlemci kullandığı için Dockerfile dosyasındaki `FROM python:3.11-slim` satırı otomatik uyum sağlar, ekstra ayar gerekmez.*

---

## 🏠 Seçenek 3: Evdeki Eski Bilgisayar / Raspberry Pi
Eğer evinizde kullanmadığınız eski bir laptop veya Raspberry Pi varsa, bunu sunucuya dönüştürebilirsiniz.
- **Avantaj:** Tamamen ücretsiz, kontrol sizde.
- **Dezavantaj:** Elektrik ve internet kesintisi riski.

---

## 🛠️ Kurulum Adımları (Tüm Yöntemler İçin Ortak)

Sunucunuza (GCP, Oracle veya VPS) SSH ile bağlandıktan sonra sırasıyla şu komutları çalıştırın:

### 1. Sistemi Güncelleyin ve Docker'ı Kurun
```bash
# Sistem güncelleme
sudo apt update && sudo apt upgrade -y

# Docker kurulumu
sudo apt install docker.io docker-compose -y

# Docker servisini başlatma
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Projeyi Sunucuya Çekin
Github kullanıyorsanız:
```bash
sudo apt install git -y
git clone https://github.com/KULLANICI_ADI/kripto-bot.git
cd kripto-bot
```
*(Github yoksa dosyaları bilgisayarınızdan sunucuya kopyalayın)*

### 3. .env Dosyasını Oluşturun
```bash
nano .env
```
*(İçeriği yapıştırın, CTRL+X, Y, Enter ile kaydedin)*

### 4. Botu Başlatın 🚀
```bash
# Arka planda başlatmak için
sudo docker-compose up -d --build
```

### Yönetim Komutları
- **Logları İzle:** `sudo docker-compose logs -f bot`
- **Durdur:** `sudo docker-compose down`
- **Yeniden Başlat:** `sudo docker-compose restart`

---

### ❓ Neden Firebase veya Vercel Olmaz?
Firebase Functions, Vercel veya Netlify gibi servisler "Web Siteleri" veya "Kısa Süreli İşlemler" içindir.
- Bizim botumuz **Sürekli (7/24)** çalışan bir döngüye sahiptir.
- Bu servisler işlem bittikten sonra sunucuyu uyutur, bu da botun durması demektir.
- Yukarıdaki **GCP** veya **Oracle** yöntemleri ise size ait sanal bir bilgisayar verir, bu yüzden bot hiç durmadan çalışabilir.
