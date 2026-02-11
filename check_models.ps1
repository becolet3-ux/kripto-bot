$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Checking for trained models..."
ssh -i $pem $opts $ip "ls -la ~/kripto-bot/models"
