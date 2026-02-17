# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Remote docker-compose.yml..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "cat ~/kripto-bot/docker-compose.yml"

Write-Host "`nChecking Remote config folder..."
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "ls -la ~/kripto-bot/config"
