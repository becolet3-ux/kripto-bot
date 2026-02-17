# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Server Time ---"
    date
    echo "--- Fetching Last 15 Minutes of Logs ---"
    sudo docker logs --since 15m kripto-bot-live
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
