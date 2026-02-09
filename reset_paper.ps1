$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Resetting Paper Trading Data on Frankfurt Server ($IP)..."

# Remote Execution: Stop paper bot, remove data files, restart
$commands = @(
    "cd kripto-bot",
    "echo 'Stopping Paper Bot...'",
    "sudo docker-compose stop bot-paper dashboard-paper",
    "echo 'Removing Data Files (State & Stats)...'",
    "sudo rm -f data/bot_state_paper.json data/bot_stats_paper.json data/bot_activity_paper.log",
    "echo 'Restarting Paper Bot...'",
    "sudo docker-compose up -d bot-paper dashboard-paper",
    "echo 'Done. Checking logs...'",
    "sleep 5",
    "sudo docker-compose logs --tail=20 bot-paper"
)

# Join commands with && for sequential execution
$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand

Write-Host "Paper Trading Reset Complete!"
