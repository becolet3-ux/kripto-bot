$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "1. Fixing Permissions on Server..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo chown -R ubuntu:ubuntu ~/kripto-bot/src && sudo chmod -R 775 ~/kripto-bot/src"

Write-Host "2. Syncing Source Code (Force)..."
scp -i $Key -o StrictHostKeyChecking=no -r src "$User@$IP`:~/kripto-bot/"

Write-Host "3. Rebuilding Live Bot (No Cache)..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose stop bot-live && sudo docker-compose rm -f bot-live && sudo docker-compose build --no-cache bot-live && sudo docker-compose up -d bot-live"

Write-Host "4. Checking Logs..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose logs --tail=50 bot-live"
