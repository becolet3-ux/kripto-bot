$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Paper Bot State..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cat kripto-bot/data/bot_state_paper.json"
