$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Starting Deployment to Frankfurt Server ($IP)..."

# 1. System Update & Docker Installation
Write-Host "`n1. Installing Docker and Dependencies..."
$installCmd = "sudo apt-get update && sudo apt-get install -y docker.io docker-compose && sudo systemctl enable docker && sudo systemctl start docker && sudo usermod -aG docker ubuntu"

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $installCmd

# 2. Prepare Directory Structure
Write-Host "`n2. Creating Directories..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "mkdir -p ~/kripto-bot/src ~/kripto-bot/config ~/kripto-bot/data ~/kripto-bot/logs"

# 3. Upload Files
Write-Host "`n3. Uploading Files..."
$filesToUpload = @(
    "src",
    "config",
    "Dockerfile",
    "docker-compose.yml",
    ".env",
    "requirements.txt"
)

foreach ($file in $filesToUpload) {
    if (Test-Path $file) {
        Write-Host "   - Uploading $file..."
        scp -i $Key -o StrictHostKeyChecking=no -r $file "$User@$IP`:~/kripto-bot/"
    } else {
        Write-Warning "   ! File/Directory not found: $file"
    }
}

# 4. Start Containers
Write-Host "`n4. Building and Starting Containers..."
$startCmd = "cd ~/kripto-bot && sudo docker-compose down && sudo docker-compose up -d --build"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $startCmd

Write-Host "`nDeployment Complete!"
Write-Host "   Live Dashboard: http://$IP/"
Write-Host "   Paper Dashboard: http://$IP:8501/"
