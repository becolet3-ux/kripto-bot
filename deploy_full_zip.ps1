# 0. Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

# 1. Ensure config and env example files exist
Write-Host "Ensuring example files exist..."
if (-not (Test-Path "config.ini.example")) {
    Write-Host "config.ini.example not found. Creating an empty one."
    New-Item "config.ini.example" -ItemType File | Out-Null
}
if (-not (Test-Path ".env.example")) {
    Write-Host ".env.example not found. Creating an empty one."
    New-Item ".env.example" -ItemType File | Out-Null
}

# 2. Ensure config files exist, creating from examples if necessary
Write-Host "Checking for config files..."
if (-not (Test-Path "config.ini")) {
    Write-Host "config.ini not found. Creating from config.ini.example."
    Copy-Item "config.ini.example" "config.ini"
}
if (-not (Test-Path ".env")) {
    Write-Host ".env not found. Creating from .env.example."
    Copy-Item ".env.example" ".env"
}

# 3. Create a clean zip file using PowerShell's built-in command
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

Write-Host "Deploying Full Update via SCP (Zip)...`n"

# 4. Upload deploy.zip to home directory
Write-Host "Uploading deploy.zip..."
scp -i $Key -o StrictHostKeyChecking=no deploy.zip "$User@$IP`:~/"

# 5. Execute remote setup and troubleshooting via a single SSH command with heredoc
Write-Host "Executing remote setup and troubleshooting..."
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    set -e
    
    echo '--- Installing dependencies ---'
    sudo apt-get update -qq && sudo apt-get install -y -qq unzip
    
    echo '--- Cleaning up old directory ---'
    sudo rm -rf ~/kripto-bot
    
    echo '--- Creating project directory ---'
    mkdir -p ~/kripto-bot
    
    echo '--- Extracting Update ---'
    unzip -o ~/deploy.zip -d ~/kripto-bot
    
    cd ~/kripto-bot
    
    echo '--- Ensuring host data/logs directories ---'
    if [ -f data ]; then sudo rm -f data; fi
    if [ -f logs ]; then sudo rm -f logs; fi
    sudo mkdir -p data logs
    sudo chown -R ubuntu:ubuntu data logs || true
    sudo chmod -R 775 data logs || true
    
    echo '--- Rebuilding and Starting ---'
    sudo docker-compose up --build -d --force-recreate
    
    echo '--- Waiting for services to start ---'
    sleep 15
    
    echo '--- TROUBLESHOOTING INFO ---'
    echo '--- Docker PS Output ---'
    sudo docker ps -a
    echo
    echo '--- Netstat Output for Port 80 ---'
    sudo netstat -tulpn | grep ':80' || echo 'Port 80 is not in use'
    echo
    echo '--- Docker Compose Logs for dashboard-live ---'
    sudo docker-compose logs --tail=50 dashboard-live
"@

Write-Host "`nDeployment and Troubleshooting Completed Successfully."
