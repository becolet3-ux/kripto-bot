$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Checking logs..."
ssh -i $pem $opts $ip "sudo docker-compose logs --tail=50 bot"
