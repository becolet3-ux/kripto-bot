# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Checking Data Persistence ---"
    ls -lh data/
    ls -lh data/*.csv 2>/dev/null
    ls -lh data/*.json 2>/dev/null
    ls -lh data/*.pkl 2>/dev/null
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
