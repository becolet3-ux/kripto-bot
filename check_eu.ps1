$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "1. Checking SSH Connection & Binance Access..."
# Check SSH and run curl in one go
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "echo '✅ SSH OK' && curl -I -s https://api.binance.com | head -n 1"
