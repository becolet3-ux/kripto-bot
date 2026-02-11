$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Cleaning up Disk Space..."
# 1. Remove stopped containers
# 2. Remove unused images
# 3. Remove build cache
ssh -i $pem $opts $ip "sudo docker system prune -a -f --volumes"

Write-Host "Checking Disk Space..."
ssh -i $pem $opts $ip "df -h"

Write-Host "Retrying Build..."
ssh -i $pem $opts $ip "cd kripto-bot && sudo docker-compose up -d --build bot-live dashboard-live"

Write-Host "Checking logs..."
Start-Sleep -Seconds 10
ssh -i $pem $opts $ip "sudo docker logs --tail 50 kripto-bot-live"

Write-Host "Done!"
