$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Resetting Live Bot Data (State & Stats) on Frankfurt Server ($IP)..."

# Remote Execution: Stop live bot, remove data files, restart
$commands = @(
    "cd kripto-bot",
    "echo 'Stopping Live Bot...'",
    "sudo docker-compose stop bot-live dashboard-live",
    "echo 'Removing Live Data Files (Forces Wallet Re-Sync)...'",
    "sudo rm -f data/bot_state_live.json data/bot_stats_live.json data/bot_activity_live.log",
    "echo 'Restarting Live Bot...'",
    "sudo docker-compose up -d bot-live dashboard-live",
    "echo 'Waiting for initialization...'",
    "sleep 10",
    "echo 'Checking Live Bot Logs (Balance Info)...'",
    "sudo docker-compose logs --tail=50 bot-live"
)

# Join commands with && for sequential execution
$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand

Write-Host "Live Bot Reset & Re-Sync Complete!"
