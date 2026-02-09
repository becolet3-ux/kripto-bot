$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking live logs..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker logs --tail 200 kripto-bot-live"
