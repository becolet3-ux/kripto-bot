$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "--- LIVE LOGS (Last 300 lines) ---"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker logs --tail 300 kripto-bot-live"

Write-Host "`n--- PAPER LOGS (Last 300 lines) ---"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker logs --tail 300 kripto-bot-paper"
