
$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$cmd = "cd kripto-bot && sudo docker-compose logs --tail=100 bot-live 2>&1"

ssh -i $pem -o StrictHostKeyChecking=no $ip $cmd
