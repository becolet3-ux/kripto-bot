# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @"
    cd ~/kripto-bot
    echo '--- Bot Startup Logs (Head 100) ---'
    sudo docker-compose logs bot-live | head -n 100
"@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
