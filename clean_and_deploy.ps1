$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Stopping Containers..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot; sudo docker-compose down"

# Prune again just to be sure we start fresh with space
Write-Host "Pruning Docker Images..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker system prune -a -f --volumes"

Write-Host "Updating Files (Lightweight Requirements & Disabled Dashboards)..."
# Upload requirements.txt (light)
scp -i $Key -o StrictHostKeyChecking=no requirements.txt "$User@$IP`:~/kripto-bot/requirements.txt"
# Upload docker-compose.yml (disabled dashboards)
scp -i $Key -o StrictHostKeyChecking=no docker-compose.yml "$User@$IP`:~/kripto-bot/docker-compose.yml"
# Upload Code Fixes
scp -i $Key -o StrictHostKeyChecking=no src/ml/ensemble_manager.py "$User@$IP`:~/kripto-bot/src/ml/ensemble_manager.py"
scp -i $Key -o StrictHostKeyChecking=no src/execution/executor.py "$User@$IP`:~/kripto-bot/src/execution/executor.py"
scp -i $Key -o StrictHostKeyChecking=no src/risk/position_sizer.py "$User@$IP`:~/kripto-bot/src/risk/position_sizer.py"
scp -i $Key -o StrictHostKeyChecking=no src/strategies/analyzer.py "$User@$IP`:~/kripto-bot/src/strategies/analyzer.py"

Write-Host "Forcing Rebuild (Lightweight)..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot; sudo docker-compose build --no-cache bot-live bot-paper"

Write-Host "Restarting Containers..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot; sudo docker-compose up -d"

Write-Host "Done. Waiting for startup..."
Start-Sleep -Seconds 10
Write-Host "Check logs manually now."
