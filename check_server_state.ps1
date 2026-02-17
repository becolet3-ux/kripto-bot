# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- creating directories ---"
    mkdir -p data logs
    chmod -R 777 data logs
    ls -ld data logs
    
    echo "--- Checking src/main.py content ---"
    grep "if not is_usdt_pair or not is_active" src/main.py
    grep "settings.SYMBOLS = active_symbols" src/main.py
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
