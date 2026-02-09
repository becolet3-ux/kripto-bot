$key = "kripto-bot-eu.pem"
$host_ip = "3.67.98.132"
$user = "ubuntu"
$remote_path = "~/kripto-bot/src"

Write-Host "Uploading src/main.py..."
scp -i $key -o StrictHostKeyChecking=no src/main.py ${user}@${host_ip}:${remote_path}/main.py

Write-Host "Uploading src/strategies/analyzer.py..."
scp -i $key -o StrictHostKeyChecking=no src/strategies/analyzer.py ${user}@${host_ip}:${remote_path}/strategies/analyzer.py

Write-Host "Restarting Live Bot..."
ssh -i $key -o StrictHostKeyChecking=no ${user}@${host_ip} "cd kripto-bot && sudo docker-compose restart bot-live"

Write-Host "Checking Logs..."
Start-Sleep -Seconds 5
ssh -i $key -o StrictHostKeyChecking=no ${user}@${host_ip} "cd kripto-bot && sudo docker-compose logs --tail 50 bot-live"
