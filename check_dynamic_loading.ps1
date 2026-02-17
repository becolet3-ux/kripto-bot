# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @"
    cd ~/kripto-bot
    sudo docker-compose logs --no-log-prefix bot-live > full_logs.txt 2>&1
    grep -i "Fetching" full_logs.txt
    grep -i "Scanning List" full_logs.txt
    grep -i "Using default list" full_logs.txt
    rm full_logs.txt
"@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
