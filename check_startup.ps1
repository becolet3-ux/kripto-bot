$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Container Status and Logs...`n"

$commands = @(
    "cd kripto-bot",
    "sudo docker-compose ps",
    "echo ' '",
    "echo '--- Last 50 lines of bot-live ---'",
    "sudo docker-compose logs --tail 50 bot-live"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand > startup_check.txt
cat startup_check.txt