$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Paper Bot Logs (Service: bot-paper)..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose logs --tail=100 bot-paper"
