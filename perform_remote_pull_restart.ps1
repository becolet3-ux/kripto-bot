$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Connecting to Frankfurt Server ($IP) to Pull and Restart...`n"

# Remote Execution: Git Pull & Docker Rebuild
$commands = @(
    "cd kripto-bot",
    "echo '--- Stashing local changes ---'",
    "git stash",
    "echo '--- Pulling latest changes ---'",
    "git pull origin main",
    "echo '--- Rebuilding and Restarting Containers ---'",
    "sudo docker-compose down",
    "sudo docker-compose up -d --build",
    "echo '--- Pruning unused images ---'",
    "sudo docker image prune -f",
    "echo '--- Checking Status ---'",
    "sleep 5",
    "sudo docker-compose ps"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
Write-Host "`nUpdate Completed."