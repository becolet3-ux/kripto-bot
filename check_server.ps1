
$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
Write-Host "Checking server connection..."
ssh -i $pem -o StrictHostKeyChecking=no $ip "ls -la"
