# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Search for Scanning List update ---"
    sudo docker-compose logs --no-log-prefix bot-live > full.log 2>&1
    grep -i "Scanning List" full.log | tail -n 20
    grep -i "Fetching ALL tickers" full.log | tail -n 20
    grep -i "No active symbols" full.log | tail -n 20
    rm full.log
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
