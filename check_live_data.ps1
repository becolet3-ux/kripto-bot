$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Checking Live Bot Data on Frankfurt Server ($IP)..."

# Fetch Logs and State File Content
$commands = @(
    "cd kripto-bot",
    "echo '--- Live Bot Logs (Last 50) ---'",
    "sudo docker-compose logs --tail=50 bot-live",
    "echo ''",
    "echo '--- Live Bot State (Balance Info) ---'",
    "sudo cat data/bot_state_live.json",
    "echo ''",
    "echo '--- Live Bot Stats ---'",
    "sudo cat data/bot_stats_live.json"
)

# Join commands with && for sequential execution
$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
