$commands = @(
    "cd kripto-bot",
    "echo '================ LIVE BOT LOGS (Last 1000 lines) - GREP ERROR ================='",
    "sudo docker-compose logs --tail 1000 bot-live 2>&1 | grep -i -E 'error|fail|exception|warning|traceback'",
    "echo ' '",
    "echo '================ LIVE BOT BALANCE CHECK ================='",
    "sudo docker-compose logs --tail 200 bot-live | grep -i 'Bakiye:'"
)

foreach ($cmd in $commands) {
    Write-Host "Executing: $cmd"
    ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 $cmd
}
