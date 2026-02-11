$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$dest = "ubuntu@3.67.98.132:~/kripto-bot/"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "STARTING DEPLOYMENT SYNC & CLEAN..."

# 1. Upload Files
Write-Host "1. Uploading requirements.txt..."
scp -i $pem $opts requirements.txt "${dest}requirements.txt"

Write-Host "2. Uploading docker-compose.yml..."
scp -i $pem $opts docker-compose.yml "${dest}docker-compose.yml"

Write-Host "3. Uploading Dockerfile..."
scp -i $pem $opts Dockerfile "${dest}Dockerfile"

Write-Host "4. Uploading src directory (Recursive)..."
scp -i $pem $opts -r src "${dest}"

# 2. Remote Execution
Write-Host "5. Executing Remote Cleanup & Rebuild..."
$commands = @(
    "echo '--- STOPPING CONTAINERS ---'",
    "cd ~/kripto-bot",
    "sudo docker-compose down",
    
    "echo '--- PRUNING SYSTEM (ALL IMAGES) ---'",
    "sudo docker system prune -a -f",
    "sudo docker volume prune -f",
    
    "echo '--- DISK USAGE CHECK ---'",
    "df -h",
    
    "echo '--- REBUILDING & STARTING ---'",
    "sudo docker-compose up -d --build",
    
    "echo '--- FINAL STATUS ---'",
    "sudo docker ps"
)

$cmd_str = $commands -join " && "
ssh -i $pem $opts $ip $cmd_str
