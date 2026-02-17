
$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"

Write-Host "🌍 Sunucuya bağlanılıyor ve temizlik başlatılıyor..." -ForegroundColor Cyan

# 1. Acil Temizlik ve Disk Kontrolü
$cmd_clean = "sudo docker system prune -a -f && echo '--- Disk Durumu ---' && df -h"
$clean_res = ssh -i $pem -o StrictHostKeyChecking=no $ip $cmd_clean
Write-Host $clean_res -ForegroundColor Green

# 2. Günlük Otomatik Temizlik (Cron Job)
# Her gün gece 04:00'te docker temizliği yapar (Logları şişirmemek için)
# Ayrıca log dosyalarını truncate eder (Docker logları bazen çok büyür)
$cron_job = "0 4 * * * sudo docker system prune -a -f && sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log"
$cmd_cron = "(crontab -l 2>/dev/null; echo '$cron_job') | sort -u | crontab -"
ssh -i $pem -o StrictHostKeyChecking=no $ip $cmd_cron

Write-Host "✅ Günlük otomatik temizlik görevi eklendi (Her gün 04:00)." -ForegroundColor Cyan
