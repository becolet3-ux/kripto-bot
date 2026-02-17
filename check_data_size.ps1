
$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
ssh -i $pem -o StrictHostKeyChecking=no $ip "ls -lh kripto-bot/data/"
