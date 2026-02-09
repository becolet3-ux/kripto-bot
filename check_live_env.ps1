$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Environment Variables in Live Bot..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker exec kripto-bot-live env | grep LOG_FILE"
