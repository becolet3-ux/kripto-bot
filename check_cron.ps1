$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Cron Jobs and Scripts on Server...`n"

$commands = @(
    "echo '--- Crontab List ---'",
    "crontab -l",
    "echo ' '",
    "echo '--- Scripts Directory ---'",
    "ls -F kripto-bot/scripts/"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand