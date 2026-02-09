$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Aggressive Docker Cleanup..."
# Stop all containers first
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker-compose down"
# Prune all unused images, containers, networks, AND volumes
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker system prune -a --volumes -f"
# Check space again
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h"
