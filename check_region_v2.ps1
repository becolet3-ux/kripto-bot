$Key = "kripto-bot.pem"
$IP = "63.182.179.139"
$User = "ubuntu"

Write-Host "Checking connectivity with OLD key ($Key)..."
# Permissions fix for windows (sometimes needed, but ssh client often handles it if in user dir)
# Using -v for verbose to see key offering
ssh -i $Key -o StrictHostKeyChecking=no -v $User@$IP "curl -I https://api.binance.com"
