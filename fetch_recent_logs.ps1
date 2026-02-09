$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Fetching Last 30 Minutes of Logs from Frankfurt Server ($IP)...`n"

# Remote Execution: Get logs since 30m for both bots
$commands = @(
    "cd kripto-bot",
    "echo '================ LIVE BOT LOGS (Last 1000 lines) ================'",
    "sudo docker-compose logs --tail 1000 bot-live",
    "echo ' '",
    "echo '================ PAPER BOT LOGS (Last 1000 lines) ================'",
    "sudo docker-compose logs --tail 1000 bot-paper"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
