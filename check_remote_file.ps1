# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking remote file content..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "grep -C 5 'sync_wallet' ~/kripto-bot/src/execution/executor.py"
