$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Reading Auto Train Script...`n"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "cat kripto-bot/scripts/auto_train_ml.sh"