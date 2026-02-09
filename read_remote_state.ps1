$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Reading remote bot state..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cat /home/ubuntu/kripto-bot/bot_state_live.json"
