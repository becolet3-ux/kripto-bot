$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Updating Cron Job to Weekly Schedule...`n"

# 1. Read current crontab, replace the line, and apply new crontab
# Original: 0 3 1 * * ... (Monthly)
# New:      0 3 * * 1 ... (Weekly - Monday)

$commands = @(
    "echo '--- Backing up Crontab ---'",
    "crontab -l > crontab.bak",
    "echo '--- Updating Schedule ---'",
    "crontab -l | sed 's|0 3 1 \* \* /home/ubuntu/kripto-bot/scripts/auto_train_ml.sh|0 3 * * 1 /home/ubuntu/kripto-bot/scripts/auto_train_ml.sh|' > crontab.new",
    "crontab crontab.new",
    "echo '--- Verifying New Crontab ---'",
    "crontab -l"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand