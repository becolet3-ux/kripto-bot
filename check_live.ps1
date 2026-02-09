$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Live Bot Status..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose ps"

Write-Host "Checking Live Bot Logs..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose logs --tail=50 bot-live"
