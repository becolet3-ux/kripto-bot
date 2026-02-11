$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Connecting to remote server for ROBUST AGGRESSIVE CLEANUP & DEPLOY..."

$commands = @(
    "echo '--- STOPPING CONTAINERS ---'",
    "cd ~/kripto-bot",
    "sudo docker-compose down",
    
    "echo '--- PRUNING SYSTEM (ALL IMAGES) ---'",
    "sudo docker system prune -a -f",
    "sudo docker volume prune -f",
    
    "echo '--- DISK USAGE AFTER CLEANUP ---'",
    "df -h",
    
    "echo '--- PULLING LATEST CODE ---'",
    "git pull",
    
    "echo '--- REBUILDING & STARTING (This will take time) ---'",
    "sudo docker-compose up -d --build",
    
    "echo '--- FINAL STATUS ---'",
    "sudo docker ps"
)

$cmd_str = $commands -join " && "
ssh -i $pem $opts $ip $cmd_str
