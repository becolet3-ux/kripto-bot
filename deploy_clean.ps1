# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

# Create zip locally
Write-Host "Creating deploy.zip..."
if (Test-Path "deploy.zip") { Remove-Item "deploy.zip" }
$filesToZip = @(
    "src",
    "scripts",
    "config",
    "Proje_Algoritma_ve_Mimari.md",
    "requirements.txt",
    "requirements_dashboard.txt",
    "docker-compose.yml",
    "Dockerfile",
    "Dockerfile.dashboard",
    "config.ini",
    ".env"
)
Compress-Archive -Path $filesToZip -DestinationPath deploy.zip -Force

# Upload
Write-Host "Uploading deploy.zip..."
scp -i $Key -o StrictHostKeyChecking=no deploy.zip "$User@$IP`:~/"

# Remote Execution
Write-Host "Executing clean deployment..."
$Script = @"
    set -e
    
    echo '🛑 Stopping containers...'
    cd ~/kripto-bot || true
    sudo docker-compose down || true
    
    echo '🧹 Pruning docker system (aggressive)...'
    sudo docker system prune -a -f --volumes
    
    echo '🧹 Cleaning APT cache...'
    sudo apt-get clean
    sudo rm -rf /var/lib/apt/lists/*
    
    echo '📂 Preparing directory...'
    sudo rm -rf ~/kripto-bot
    mkdir -p ~/kripto-bot
    
    echo '📦 Extracting Update...'
    sudo apt-get update -qq && sudo apt-get install -y -qq unzip
    unzip -o ~/deploy.zip -d ~/kripto-bot
    
    echo '🗑️ Removing zip...'
    rm ~/deploy.zip
    
    echo '🚀 Building and Starting...'
    cd ~/kripto-bot
    # Build dashboard first to ensure it gets space
    sudo docker-compose build dashboard-live
    sudo docker-compose build bot-live
    sudo docker-compose up -d
    
    echo '✅ Done! Checking logs...'
    sleep 10
    sudo docker ps
    sudo docker-compose logs --tail=20 dashboard-live
"@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
