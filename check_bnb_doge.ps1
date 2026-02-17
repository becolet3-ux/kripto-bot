# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Search for BNB Protection Events ---"
    sudo docker logs kripto-bot-live 2>&1 | grep -i "BNB" | tail -n 50
    
    echo "--- Search for DOGE Transactions ---"
    # Use single quotes for grep pattern to avoid shell expansion issues
    sudo docker logs kripto-bot-live 2>&1 | grep -i "DOGE" | grep -E "SELL|EXIT|Closed|BUY" | tail -n 20
    
    echo "--- Search for Dust Conversion ---"
    sudo docker logs kripto-bot-live 2>&1 | grep -E "Dust|convert|Redeem" | tail -n 20
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
