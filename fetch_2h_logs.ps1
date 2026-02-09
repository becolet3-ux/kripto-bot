$key = "kripto-bot-eu.pem"
$host_ip = "3.67.98.132"
$user = "ubuntu"

Write-Host "Fetching last 2 hours of logs from Frankfurt Server..."

$commands = @(
    "cd kripto-bot && echo '================ LIVE BOT ERRORS (Last 2h) ================='",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-live | grep -i -E 'error|fail|exception|warning|traceback' | tail -n 50",
    "echo ' '",
    "echo '================ LIVE BOT ACTIVITY SUMMARY (Last ~2h) ================='",
    "echo '--- Signals Detected ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-live | grep 'Signal Detected' | tail -n 10",
    "echo '--- Entries/Exits ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-live | grep -E 'Entry triggered|Exiting|Selling' | tail -n 10",
    "echo '--- Balance Checks ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-live | grep 'Bakiye:' | tail -n 5",
    "echo ' '",
    "echo '================ PAPER BOT ERRORS (Last ~2h) ================='",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-paper | grep -i -E 'error|fail|exception|warning|traceback' | tail -n 50",
    "echo ' '",
    "echo '================ PAPER BOT ACTIVITY SUMMARY (Last ~2h) ================='",
    "echo '--- Signals Detected ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-paper | grep 'Signal Detected' | tail -n 10",
    "echo '--- Entries/Exits ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 5000 bot-paper | grep -E 'Entry triggered|Exiting|Selling' | tail -n 10"
)

foreach ($cmd in $commands) {
    # Write-Host "Executing: $cmd"
    ssh -i $key -o StrictHostKeyChecking=no ${user}@${host_ip} $cmd
}
