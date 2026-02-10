$pem = "kripto-bot-eu.pem"
$host_ip = "ubuntu@3.67.98.132"
ssh -i $pem -o StrictHostKeyChecking=no $host_ip "sudo docker ps -a"
