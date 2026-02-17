# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Starting Manual Debug..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    echo '--- Disk Space ---'
    df -h
    echo ''
    
    echo '--- Project Directory ---'
    ls -la ~/kripto-bot
    echo ''
    
    echo '--- Manual Docker Compose Up ---'
    cd ~/kripto-bot
    sudo docker-compose up -d
    echo ''
    
    echo '--- Dashboard /app/src Listing ---'
    sudo docker-compose exec -T dashboard-live ls -la /app/src || echo 'ls failed'
    echo ''
    
    echo '--- Docker PS After Up ---'
    sudo docker ps -a
    echo ''
    
    echo '--- Logs Immediately After Up ---'
    sudo docker-compose logs --tail=20 dashboard-live
"@
