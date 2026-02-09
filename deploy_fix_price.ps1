$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Deploying fixes..."
scp -i $Key -o StrictHostKeyChecking=no src/main.py "$User@${IP}:/home/ubuntu/kripto-bot/src/main.py"
scp -i $Key -o StrictHostKeyChecking=no src/execution/executor.py "$User@${IP}:/home/ubuntu/kripto-bot/src/execution/executor.py"

Write-Host "Restarting live bot..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker restart kripto-bot-live"

Write-Host "Deployment complete."
