$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "1. Stopping Paper Bot..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker stop kripto-bot-paper"

Write-Host "2. Resetting Paper State Again (to clear bad data)..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo python3 reset_paper_state.py"

Write-Host "3. Uploading docker-compose.yml & .dockerignore..."
# Quoted destination to avoid PowerShell parsing issues
scp -i $Key -o StrictHostKeyChecking=no docker-compose.yml "$User@$IP`:~/kripto-bot/docker-compose.yml"
scp -i $Key -o StrictHostKeyChecking=no .dockerignore "$User@$IP`:~/kripto-bot/.dockerignore"
scp -i $Key -o StrictHostKeyChecking=no requirements.txt "$User@$IP`:~/kripto-bot/requirements.txt"
scp -i $Key -o StrictHostKeyChecking=no Dockerfile "$User@$IP`:~/kripto-bot/Dockerfile"

Write-Host "4. Cleaning up Disk Space & Syncing SRC..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo rm -f data/*.log && sudo docker system prune -f"
# Using tar for faster transfer of many small files
tar -czf src.tar.gz src
scp -i $Key -o StrictHostKeyChecking=no src.tar.gz "$User@$IP`:~/kripto-bot/src.tar.gz"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && tar -xzf src.tar.gz && rm src.tar.gz"
Remove-Item src.tar.gz

Write-Host "5. Recreating Paper Bot with New Config..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot && sudo docker-compose stop bot-paper && sudo docker-compose rm -f bot-paper && sudo docker-compose up -d --build bot-paper"

Write-Host "6. Checking Logs (Watching for 'Real Data' confirmation)..."
Start-Sleep -Seconds 10
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker logs --tail 20 kripto-bot-paper"
