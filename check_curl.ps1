$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "curl -I http://localhost:80"
