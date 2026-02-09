$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Starting Deployment to Frankfurt Server ($IP)..."

# 1. Upload Critical Files
Write-Host "Uploading Files..."
$files = @(
    "src/execution/executor.py",
    "src/risk/position_sizer.py",
    "src/strategies/analyzer.py",
    "src/ml/ensemble_manager.py",
    "config/settings.py",
    "requirements.txt",
    "docker-compose.yml"
)

foreach ($file in $files) {
    Write-Host "   - $file"
    scp -i $Key -o StrictHostKeyChecking=no $file "$User@$IP`:~/kripto-bot/$file"
}

# 2. Remote Execution: Clean and Rebuild
Write-Host "Remote Execution: Clean and Rebuild..."
# Use simple commands without complex quoting if possible
$commands = @(
    "cd kripto-bot",
    "rm -f src/execution/position_sizer.py",
    "echo 'Stopping containers...'",
    "sudo docker-compose down",
    "echo 'Cleaning disk space...'",
    "sudo docker system prune -a -f",
    "echo 'Building and Starting...'",
    "sudo docker-compose up -d --build",
    "echo 'Done. Checking logs...'",
    "sleep 10",
    "sudo docker-compose logs --tail=50"
)

# Join with && for Linux shell execution
$cmd_str = $commands -join " && "
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $cmd_str

Write-Host "Deployment Complete!"
