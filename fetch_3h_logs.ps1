$commands = @(
    "cd kripto-bot && echo '================ LIVE BOT ERRORS (Last 3h) ================='",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-live | grep -i -E 'error|fail|exception|warning|traceback' | tail -n 50",
    "echo ' '",
    "echo '================ LIVE BOT ACTIVITY SUMMARY (Last ~3h) ================='",
    "echo '--- Signals Detected ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-live | grep 'Signal Detected' | tail -n 10",
    "echo '--- Entries/Exits ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-live | grep -E 'Entry triggered|Exiting|Selling' | tail -n 10",
    "echo '--- Balance Checks ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-live | grep 'Bakiye:' | tail -n 5",
    "echo ' '",
    "echo '================ PAPER BOT ERRORS (Last ~3h) ================='",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-paper | grep -i -E 'error|fail|exception|warning|traceback' | tail -n 50",
    "echo ' '",
    "echo '================ PAPER BOT ACTIVITY SUMMARY (Last ~3h) ================='",
    "echo '--- Signals Detected ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-paper | grep 'Signal Detected' | tail -n 10",
    "echo '--- Entries/Exits ---'",
    "cd kripto-bot && sudo docker-compose logs --tail 8000 bot-paper | grep -E 'Entry triggered|Exiting|Selling' | tail -n 10"
)

foreach ($cmd in $commands) {
    ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "$cmd"
}
