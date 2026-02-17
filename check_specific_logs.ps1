# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Server Time ---"
    date
    echo "--- Fetching Last 1 Hour of Logs ---"
    # Grep for DOGE and BNB to focus on relevant lines, but also get context
    sudo docker logs --since 1h kripto-bot-live | grep -E "DOGE|BNB|SELL|BUY|ENTRY|EXIT|Protection|score"
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
