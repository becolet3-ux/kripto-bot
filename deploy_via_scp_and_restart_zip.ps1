$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Deploying updates via SCP (Zip Method - Python Unzip)...`n"

# 1. Upload src.zip
Write-Host "Uploading src.zip..."
scp -i $Key -o StrictHostKeyChecking=no src.zip $User@$IP`:~/kripto-bot/src.zip

# 2. Upload config files
Write-Host "Uploading docker-compose.yml and requirements.txt..."
scp -i $Key -o StrictHostKeyChecking=no docker-compose.yml $User@$IP`:~/kripto-bot/docker-compose.yml
scp -i $Key -o StrictHostKeyChecking=no requirements.txt $User@$IP`:~/kripto-bot/requirements.txt

# 3. Remote Commands: Extract & Restart
$commands = @(
    "cd kripto-bot",
    "echo '--- Extracting Source Code ---'",
    "rm -rf src/",
    "python3 -m zipfile -e src.zip .",
    "echo '--- Stopping Containers ---'",
    "sudo docker-compose down",
    "echo '--- Rebuilding and Starting ---'",
    "sudo docker-compose up -d --build",
    "echo '--- Pruning Images ---'",
    "sudo docker image prune -f",
    "echo '--- Status Check ---'",
    "sleep 5",
    "sudo docker-compose ps"
)

$remoteCommand = $commands -join " && "

Write-Host "Executing Remote Restart..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
Write-Host "`nDeployment Completed Successfully."