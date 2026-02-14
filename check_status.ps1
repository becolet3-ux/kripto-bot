# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking detailed status..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    echo '--- Docker PS All ---'
    sudo docker ps -a
    echo ''
    echo '--- Dashboard Logs (Last 50 lines) ---'
    cd ~/kripto-bot && sudo docker-compose logs --tail=50 dashboard-live
"@
