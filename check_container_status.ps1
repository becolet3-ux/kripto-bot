$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Checking Container Status..."
ssh -i $pem $opts $ip "sudo docker ps -a"

Write-Host "Checking Logs..."
ssh -i $pem $opts $ip "cd ~/kripto-bot && sudo docker-compose logs --tail=20 bot-live"
