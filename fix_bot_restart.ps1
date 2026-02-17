# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Fixing Bot Restart Loop..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    cd ~/kripto-bot
    echo 'Stopping and removing container...'
    sudo docker-compose stop bot-live
    sudo docker-compose rm -f bot-live
    
    echo 'Starting container...'
    sudo docker-compose up -d --force-recreate bot-live
    
    echo 'Waiting for container to initialize...'
    sleep 5
    
    echo 'Checking /app content in container...'
    sudo docker exec kripto-bot-live ls -la /app
    sudo docker exec kripto-bot-live ls -la /app/config || echo 'Config not found in container'
    
    echo 'Checking logs...'
    sudo docker-compose logs --tail=20 bot-live
"@
