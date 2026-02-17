$Minutes = 1
$Pattern = "ml_training_data.csv|DB Log Error"

Write-Output "Filtering logs for last $Minutes minute(s)..."

$cmd = "sudo docker logs --since ${Minutes}m kripto-bot-live 2>&1 | egrep -i '$Pattern' | tail -n 400"
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 $cmd

Write-Output "Done."
