# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Search for Dust Conversion ---"
    sudo docker logs kripto-bot-live 2>&1 | grep -E "Dust|convert|Redeem" | tail -n 50
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
