$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Checking remote directory structure..."
ssh -i $pem $opts $ip "ls -la ~ && ls -la ~/kripto-bot"
