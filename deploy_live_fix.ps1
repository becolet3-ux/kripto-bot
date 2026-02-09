$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "1. Compressing Source Code..."
tar -czf src.tar.gz src

Write-Host "2. Uploading Source Code..."
scp -i $Key -o StrictHostKeyChecking=no src.tar.gz "$User@$IP`:~/kripto-bot/src.tar.gz"

Write-Host "3. Extracting Source Code on Server..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && tar -xzf src.tar.gz && rm src.tar.gz"

Write-Host "4. Restarting Live Bot..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose restart bot-live"

Write-Host "5. Cleaning Local Artifacts..."
Remove-Item src.tar.gz

Write-Host "Done! Live bot restarted with new sync logic."
