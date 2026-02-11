$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Running verification inside container (bot-live)..."
# Corrected service name from 'bot' to 'bot-live'
ssh -i $pem $opts $ip "sudo docker-compose exec -T bot-live python src/check_ml_env.py"
