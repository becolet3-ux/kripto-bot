$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "1. Creating bot_activity_live.log..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "touch ~/kripto-bot/data/bot_activity_live.log && chmod 666 ~/kripto-bot/data/bot_activity_live.log"

Write-Host "2. Syncing Source Code..."
scp -i $Key -o StrictHostKeyChecking=no -r src "$User@$IP`:~/kripto-bot/"

Write-Host "3. Restarting Live Bot..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose stop bot-live && sudo docker-compose rm -f bot-live && sudo docker-compose up -d --build bot-live"

Write-Host "4. Checking Logs..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose logs --tail=20 bot-live"
