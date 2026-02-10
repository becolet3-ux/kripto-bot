$pem = "kripto-bot-eu.pem"
$host_ip = "ubuntu@3.67.98.132"
ssh -i $pem -o StrictHostKeyChecking=no $host_ip "cd kripto-bot && sudo docker-compose restart bot-live"