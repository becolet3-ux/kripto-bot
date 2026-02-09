$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking content of bot_activity_paper.log to see if Live Bot is writing there..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "tail -n 20 ~/kripto-bot/data/bot_activity_paper.log"
