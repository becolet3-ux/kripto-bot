# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Image Content..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "sudo docker run --rm --entrypoint ls kripto-bot_bot-live -R /app"
