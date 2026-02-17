$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Updating Cron Job to DAILY Schedule...`n"

# 1. Read current crontab, replace the line, and apply new crontab
# Previous: 0 3 * * 1 ... (Weekly)
# New:      0 3 * * * ... (Daily)

$commands = @(
    "echo '--- Backing up Crontab ---'",
    "crontab -l > crontab.bak_weekly",
    "echo '--- Updating Schedule ---'",
    "crontab -l | sed 's|0 3 \* \* 1 /home/ubuntu/kripto-bot/scripts/auto_train_ml.sh|0 3 * * * /home/ubuntu/kripto-bot/scripts/auto_train_ml.sh|' > crontab.daily",
    "crontab crontab.daily",
    "echo '--- Verifying New Crontab ---'",
    "crontab -l"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand