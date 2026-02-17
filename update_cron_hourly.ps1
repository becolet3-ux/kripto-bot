$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "--- Enabling Hourly Training with HOT RELOAD ---`n"

# 1. Upload new code (EnsembleManager with Hot Reload)
Write-Host "Uploading Source Code..."
scp -i $Key -o StrictHostKeyChecking=no src_deploy.zip $User@$IP`:/home/ubuntu/kripto-bot/

# 2. Remote Operations
$commands = @(
    "cd kripto-bot",
    
    "echo '--- 1. Extracting New Code ---'",
    "sudo rm -rf src/",
    "python3 -m zipfile -e src_deploy.zip .",
    
    "echo '--- 2. Restarting Bot (One Last Time) to Apply Hot Reload Logic ---'",
    "sudo docker-compose restart bot-live",
    
    "echo '--- 3. Modifying Auto-Train Script (Disable Restart) ---'",
    "sed -i 's/sudo docker-compose restart bot-live/# sudo docker-compose restart bot-live/g' scripts/auto_train_ml.sh",
    
    "echo '--- 4. Setting Hourly Cron Schedule ---'",
    "crontab -l > crontab.bak_daily",
    "crontab -l | sed 's|0 3 \* \* \* /home/ubuntu/kripto-bot/scripts/auto_train_ml.sh|0 * * * * /home/ubuntu/kripto-bot/scripts/auto_train_ml.sh|' > crontab.hourly",
    "crontab crontab.hourly",
    
    "echo '--- 5. Verification ---'",
    "crontab -l",
    "grep 'restart' scripts/auto_train_ml.sh"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand