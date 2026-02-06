#!/bin/bash
# Kripto Bot Güncelleme Scripti

echo "========================================"
echo "🚀 Kripto Bot Güncelleme Başlatılıyor..."
echo "========================================"

# 1. Kodları Çek
echo "⬇️  Git üzerinden güncellemeler çekiliyor..."
git pull
if [ $? -ne 0 ]; then
    echo "❌ HATA: Git pull başarısız oldu. Lütfen internet bağlantısını veya çakışmaları kontrol edin."
    exit 1
fi

# 2. Docker Yeniden Derle ve Başlat
echo "🐳 Docker container'ları yeniden derleniyor ve başlatılıyor..."
sudo docker-compose up -d --build

if [ $? -eq 0 ]; then
    echo "✅ Güncelleme Başarıyla Tamamlandı!"
    echo "----------------------------------------"
    echo "📜 Logları izlemek için şu komutu kullanabilirsiniz:"
    echo "   sudo docker-compose logs -f bot"
    echo "----------------------------------------"
else
    echo "❌ HATA: Docker-compose işlemi başarısız oldu."
    exit 1
fi
