$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Updating Executor & PositionSizer (Fixing Import & Class Mismatch)..."

# Upload Executor
scp -i $Key -o StrictHostKeyChecking=no src/execution/executor.py "$User@$IP`:~/kripto-bot/src/execution/executor.py"

# Upload PositionSizer (Risk module)
scp -i $Key -o StrictHostKeyChecking=no src/risk/position_sizer.py "$User@$IP`:~/kripto-bot/src/risk/position_sizer.py"

Write-Host "Forcing Rebuild (No Cache) to ensure new code is copied..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot; sudo docker-compose build --no-cache bot-live bot-paper"

Write-Host "Restarting Containers..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cd kripto-bot; sudo docker-compose up -d"

Write-Host "Done. Waiting for startup..."
Start-Sleep -Seconds 10
Write-Host "Check logs manually now."
