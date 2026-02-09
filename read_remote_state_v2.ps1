$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Reading remote bot state from data directory..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cat /home/ubuntu/kripto-bot/data/bot_state_live.json"
