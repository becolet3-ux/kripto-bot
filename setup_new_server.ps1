# Setup NEW server (Local Transfer Version)
# Usage: ./setup_new_server.ps1 <NEW_IP> [KEY_PATH]
param(
    [string]$NewIP,
    [string]$KeyPath = "kripto-bot-yeni.pem"
)

if (-not $NewIP) {
    Write-Error "Lutfen yeni IP adresini girin. Ornek: ./setup_new_server.ps1 1.2.3.4"
    exit 1
}

if (-not (Test-Path $KeyPath)) {
    Write-Error "Key dosyasi bulunamadi: $KeyPath"
    exit 1
}

$User = "ubuntu"

Write-Host "Yeni sunucuya baglaniliyor ($NewIP) - Anahtar: $KeyPath..."

# 1. Install Docker
Write-Host "Docker kuruluyor..."
$SetupCmd = "sudo apt-get update && sudo apt-get install -y docker.io docker-compose"
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP $SetupCmd

# 2. Package and Upload Code
Write-Host "Proje dosyalari paketleniyor (Git bagimsiz)..."
# Create tar excluding heavy folders
tar -cf project.tar --exclude ".git" --exclude ".venv" --exclude "local_backup_data" --exclude "project.tar" --exclude "__pycache__" .

Write-Host "Proje yukleniyor..."
scp -i $KeyPath -o StrictHostKeyChecking=no project.tar "$User@${NewIP}:/home/ubuntu/"

Write-Host "Proje aciliyor..."
$UnpackCmd = "mkdir -p kripto-bot && tar -xf project.tar -C kripto-bot && rm project.tar"
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP $UnpackCmd

# 3. Upload Config & Data
Write-Host "Ayarlar ve Veriler yukleniyor..."
# Upload .env
scp -i $KeyPath -o StrictHostKeyChecking=no .env "$User@${NewIP}:/home/ubuntu/kripto-bot/.env"

# Upload Backup Data
# Create data directory first
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP "mkdir -p kripto-bot/data"
# Upload files
scp -i $KeyPath -r -o StrictHostKeyChecking=no ./local_backup_data/* "$User@${NewIP}:/home/ubuntu/kripto-bot/data/"

# 4. Start Bot
Write-Host "Bot baslatiliyor..."
$StartCmd = "cd kripto-bot && sudo docker-compose up -d --build"
ssh -i $KeyPath -o StrictHostKeyChecking=no $User@$NewIP $StartCmd

# Cleanup local tar
Remove-Item project.tar

Write-Host "Kurulum tamamlandi! Yeni Panel: http://$NewIP/"
