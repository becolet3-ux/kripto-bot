$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Log Files in data/ directory..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "ls -la ~/kripto-bot/data/"

Write-Host "Checking content of bot_activity_live.log (tail)..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "tail -n 20 ~/kripto-bot/data/bot_activity_live.log"
