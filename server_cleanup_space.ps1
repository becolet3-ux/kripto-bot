# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Starting Disk Space Cleanup..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    echo '--- Disk Space BEFORE Cleanup ---'
    df -h
    echo ''
    
    echo '--- Pruning Docker System (Images, Containers, Cache) ---'
    sudo docker system prune -a -f --volumes
    echo ''
    
    echo '--- Cleaning APT Cache ---'
    sudo apt-get clean
    echo ''
    
    echo '--- Removing Old Log Files and Zip ---'
    sudo rm -rf /var/log/*.gz
    sudo rm -rf ~/kripto-bot/logs/*
    rm -f ~/kripto-bot/kripto-bot-full.zip
    echo ''
    
    echo '--- Disk Space AFTER Cleanup ---'
    df -h
    echo ''
    
    echo '--- Retrying Deployment ---'
    cd ~/kripto-bot
    sudo docker-compose up --build -d
    echo ''
    
    echo '--- Final Status Check ---'
    sleep 10
    sudo docker ps
"@
