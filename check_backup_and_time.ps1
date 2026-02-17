# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Server Current Time ---"
    date +%s
    date
    echo "--- Searching for Backup Directories ---"
    find . -maxdepth 2 -type d -name "*backup*" 2>/dev/null
    find . -maxdepth 2 -type d -name "*old*" 2>/dev/null
    find . -maxdepth 2 -type d -name "*data*" 2>/dev/null
    echo "--- Checking Docker Volumes ---"
    sudo docker volume ls
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
