$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Fetching Remote Bot State..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cat ~/kripto-bot/data/bot_state_live.json"
