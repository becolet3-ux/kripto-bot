$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Deploying Min Trade Fix and Resetting Paper Data on Frankfurt Server ($IP)...`n"

# 1. Upload Executor Fix
Write-Host "Uploading updated executor.py..."
scp -i $Key -o StrictHostKeyChecking=no src/execution/executor.py $User@$IP`:/home/$User/kripto-bot/src/execution/

# 2. Remote Execution: Stop, Clean Paper Data, Rebuild
Write-Host "Remote Execution: Stop, Reset Paper Data, Rebuild...`n"
$commands = @(
    "cd kripto-bot",
    "echo 'Stopping All Containers...'",
    "sudo docker-compose down",
    "echo 'Resetting PAPER Trading Data (Fixing Statistics)...'",
    "sudo rm -f data/bot_state_paper.json data/bot_stats_paper.json data/bot_activity_paper.log",
    "echo 'Building and Starting All Services...'",
    "sudo docker-compose up -d --build",
    "echo 'Waiting for initialization...'",
    "sleep 15",
    "echo 'Checking Live Bot Logs (Min Trade Amount)...'",
    "sudo docker-compose logs --tail=20 bot-live"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand

Write-Host "`nDeployment & Reset Complete!"
