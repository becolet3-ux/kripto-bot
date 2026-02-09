# Backup data from OLD server
# Usage: ./backup_data.ps1
$ErrorActionPreference = "Stop"
mkdir local_backup_data -Force
Write-Host "Eski sunucudan veriler çekiliyor..."
scp -i "kripto-bot.pem" -r -o StrictHostKeyChecking=no ubuntu@63.177.89.32:/home/ubuntu/kripto-bot/data/* ./local_backup_data/
Write-Host "Yedekleme tamamlandı: ./local_backup_data/"