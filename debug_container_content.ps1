# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Getting Docker Images..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "sudo docker images"
