$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"
$RemotePath = "/home/ubuntu/kripto-bot/bot_state_live.json"
$LocalPath = "C:\Users\emdam\Documents\trae_projects\kripto-bot\bot_state_live_investigation.json"

Write-Host "Fetching bot state..."
scp -i $Key -o StrictHostKeyChecking=no "$User@${IP}:$RemotePath" $LocalPath

Write-Host "Fetching recent logs..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker logs --tail 500 kripto-bot-live" > C:\Users\emdam\Documents\trae_projects\kripto-bot\live_logs_investigation.txt
