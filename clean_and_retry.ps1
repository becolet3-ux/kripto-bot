# Clean and Retry Docker
param(
    [string]$NewIP,
    [string]$KeyPath = "kripto-bot-yeni.pem"
)

$User = "ubuntu"

# 1. Clean Docker
Write-Host "Docker temizleniyor..."
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP "sudo docker system prune -a -f"

# 2. Start
Write-Host "Bot tekrar baslatiliyor..."
$StartCmd = "cd kripto-bot && sudo docker-compose up -d --build"
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP $StartCmd

Write-Host "Islem tamamlandi."
