$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Deploying Dashboard Fixes to Frankfurt Server ($IP)..."

# 1. Dosya Transferi (Sadece değişenler)
Write-Host "Uploading configuration files..."
scp -i $Key -o StrictHostKeyChecking=no requirements.txt $User@$IP`:/home/$User/kripto-bot/
scp -i $Key -o StrictHostKeyChecking=no docker-compose.yml $User@$IP`:/home/$User/kripto-bot/

# 2. Remote Execution: Clean and Rebuild
Write-Host "Remote Execution: Clean, Rebuild and Start..."
# Use simple commands without complex quoting if possible
$commands = @(
    "cd kripto-bot",
    "echo 'Stopping containers...'",
    "sudo docker-compose down",
    "echo 'Cleaning disk space (pruning unused images)...'",
    "sudo docker system prune -a -f",
    "echo 'Building and Starting Services...'",
    "sudo docker-compose up -d --build",
    "echo 'Done. Checking running containers...'",
    "sleep 10",
    "sudo docker ps"
)

# Join commands with && for sequential execution
$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand

Write-Host "Deployment Complete!"
