$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Fetching Latest Logs (Focus on Errors) from Frankfurt Server ($IP)...`n"

# Remote Execution: Get logs
$commands = @(
    "cd kripto-bot",
    "echo '================ LIVE BOT ERRORS (Last 200 lines) ================'",
    "sudo docker-compose logs --tail 200 bot-live",
    "echo ' '",
    "echo '================ LIVE BOT ERROR GREP ================'",
    "sudo docker-compose logs bot-live | grep -i -E 'error|fail|exception|warning|traceback' | tail -n 20"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
