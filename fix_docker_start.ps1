# Fix Docker Start (Manual Binary Install)
param(
    [string]$NewIP,
    [string]$KeyPath = "kripto-bot-yeni.pem"
)

$User = "ubuntu"

# 1. Install Docker Compose v2 Binary
Write-Host "Docker Compose v2 yukleniyor..."
$InstallCmd = "sudo curl -SL https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP $InstallCmd

# 2. Start
Write-Host "Bot baslatiliyor..."
$StartCmd = "cd kripto-bot && sudo docker-compose down --remove-orphans && sudo docker-compose up -d --build"
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP $StartCmd

Write-Host "Islem tamamlandi."
