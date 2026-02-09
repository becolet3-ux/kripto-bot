$Key = "kripto-bot-yeni.pem"
$IP = "63.182.179.139"
$User = "ubuntu"

Write-Host "Checking connectivity..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "curl -I https://api.binance.com"
