$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Deploying updates via SCP (No Git on Server)...`n"

# 1. Upload src.tar.gz
Write-Host "Uploading src.tar.gz..."
scp -i $Key -o StrictHostKeyChecking=no src.tar.gz $User@$IP`:~/kripto-bot/src.tar.gz

# 2. Upload config files
Write-Host "Uploading docker-compose.yml and requirements.txt..."
scp -i $Key -o StrictHostKeyChecking=no docker-compose.yml $User@$IP`:~/kripto-bot/docker-compose.yml
scp -i $Key -o StrictHostKeyChecking=no requirements.txt $User@$IP`:~/kripto-bot/requirements.txt

# 3. Remote Commands: Extract & Restart
$commands = @(
    "cd kripto-bot",
    "echo '--- Extracting Source Code ---'",
    "rm -rf src/",
    "tar -xzf src.tar.gz",
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