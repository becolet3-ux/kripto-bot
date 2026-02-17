$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Deploying FULL updates (src + scripts + docs) with AGGRESSIVE CLEANUP...`n"

# 1. Upload deploy.zip
Write-Host "Uploading deploy.zip..."
scp -i $Key -o StrictHostKeyChecking=no deploy.zip $User@$IP`:~/kripto-bot/deploy.zip

# 2. Upload Documentation
Write-Host "Uploading Documentation..."
scp -i $Key -o StrictHostKeyChecking=no Proje_Algoritma_ve_Mimari.md $User@$IP`:~/kripto-bot/Proje_Algoritma_ve_Mimari.md

# 3. Remote Commands: Extract & Restart
$commands = @(
    "cd kripto-bot",
    
    "echo '--- Stopping Containers ---'",
    "sudo docker-compose down",
    
    "echo '--- FREEING DISK SPACE (Aggressive) ---'",
    "sudo docker system prune -a -f",
    "sudo journalctl --vacuum-time=1s",
    "sudo rm -rf /var/log/*.gz",
    
    "echo '--- Cleaning Old Code ---'",
    "sudo rm -rf src/ scripts/",
    
    "echo '--- Extracting Updates ---'",
    "python3 -m zipfile -e deploy.zip .",
    "chmod +x scripts/*.sh",
    
    "echo '--- Rebuilding and Starting ---'",
    "sudo docker-compose up -d --build",
    
    "echo '--- Status Check ---'",
    "sleep 10",
    "sudo docker-compose ps"
)

$remoteCommand = $commands -join " && "

Write-Host "Executing Remote Restart..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
Write-Host "`nDeployment Completed Successfully."
