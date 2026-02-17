$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Debugging Remote File Structure...`n"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "ls -F kripto-bot/"
Write-Host "`nChecking src content:"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "ls -F kripto-bot/src/"