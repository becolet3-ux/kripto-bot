# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @"
    cd ~/kripto-bot
    echo '--- Dashboard Logs (Last 100 lines) ---'
    sudo docker-compose logs --tail=100 dashboard-live
"@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
