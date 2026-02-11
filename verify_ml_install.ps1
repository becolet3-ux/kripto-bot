$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Verifying ML Library Installation on Remote..."

# Using simple concatenation to avoid escaping hell
$cmd = "sudo docker-compose exec -T bot python -c 'import sklearn; print(\"Scikit-Learn Version: \" + sklearn.__version__)'"

ssh -i $pem $opts $ip $cmd
