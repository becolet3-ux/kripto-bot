$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Disk Space..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h"
