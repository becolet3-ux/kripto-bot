# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    head -n 20 ~/kripto-bot/data/bot_state_live.json
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
