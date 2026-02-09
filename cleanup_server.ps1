$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Disk Usage BEFORE Cleanup..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h"

Write-Host "Cleaning up Docker (Aggressive)..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker system prune -a -f --volumes"

Write-Host "Checking Disk Usage AFTER Cleanup..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h"
