# 🚀 Kripto Bot Kurulum ve Dağıtım Rehberi

Bilgisayarınızın sürekli açık kalmasına gerek kalmadan, botunuzu 7/24 çalışır halde tutmak için aşağıdaki yöntemleri kullanabilirsiniz.

---

## 💰 Seçenek 1: Ücretli VPS (En Kolay ve Stabil)
Aylık 5-10$ maliyetle en sorunsuz yöntemdir. (DigitalOcean, Hetzner, vb.)
*Kurulum adımları dosyanın en altında mevcuttur.*

---

## 🆓 Seçenek 2: Tamamen Ücretsiz Yöntemler

Sürekli açık bir sunucu için "Sonsuza Kadar Ücretsiz" (Always Free) paketleri olan bulut sağlayıcıları kullanabilirsiniz. Kurulum biraz daha teknik bilgi gerektirebilir ancak **ücretsizdir**.

### A. AWS Free Tier (✅ EN İYİ ALTERNATİF - 1 Yıl Ücretsiz)
Oracle sorunu yaşayanlar için en iyi seçenek Amazon Web Services (AWS) kullanmaktır.
*   **Süre:** Yeni üyelere 12 ay boyunca ücretsiz.
*   **Bölge:** Frankfurt (eu-central-1) veya İrlanda seçerek Binance yasağından kurtulabilirsiniz.
*   **Sunucu:** **t2.micro** veya **t3.micro** (1 vCPU, 1 GB RAM).

**Kurulum Adımları:**
1.  [AWS Free Tier](https://aws.amazon.com/free/) sayfasına gidip hesap oluşturun.
2.  Giriş yaptıktan sonra sağ üstten bölgeyi **Frankfurt (eu-central-1)** seçin (Önemli!).
3.  **EC2** servisini aratıp açın ve **Launch Instance** (Sunucu Başlat) butonuna tıklayın.
4.  **Name:** `kripto-bot` yazın.
5.  **OS Image:** `Ubuntu Server 22.04 LTS` seçin (Free Tier Eligible yazar).
6.  **Instance Type:** `t2.micro` (veya t3.micro) seçin.
7.  **Key Pair:** "Create new key pair" diyip bir isim verin ve `.pem` dosyasını indirin (Bunu kaybetmeyin!).
8.  **Launch Instance** diyerek başlatın.
9.  Bağlanmak için indirilen `.pem` dosyasını kullanacaksınız.

### B. Google Cloud Platform (GCP) - Always Free (⚠️ DİKKAT: Binance İçin Uygun Değil)
Google, `us-central1` gibi ABD bölgelerinde ücretsiz sunucu verir.
**Ancak Binance Global, ABD IP'lerini engeller (Hata Kodu: 451).**
Bu yüzden bot için GCP Free Tier **kullanılamaz**. Avrupa seçerseniz aylık 7-10$ ücret çıkar.

### C. Oracle Cloud Free Tier (Zor Kayıt)
Oracle kayıt aşamasında çok fazla hata verebilir. Eğer kaydolabilirseniz en güçlüsüdür, ancak kayıt olmak zordur.
1.  **Home Region** seçerken **Germany Central (Frankfurt)** veya **Netherlands** seçin.
2.  **VM.Standard.A1.Flex** (ARM) sunucu oluşturun.

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
