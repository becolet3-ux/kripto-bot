$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Fetching Last 12 Hours of Logs from Frankfurt Server ($IP)...`n"

# Remote Execution: Get logs since 12h for live bot
$commands = @(
    "cd kripto-bot",
    "echo '================ LIVE BOT LOGS (Last 12 Hours) ================'",
    "sudo docker-compose logs --since 12h bot-live"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand > logs_12h.txt
Write-Host "Logs saved to logs_12h.txt"