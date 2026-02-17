# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

# Upload the python script
scp -i $Key -o StrictHostKeyChecking=no reset_stats.py "$User@$IP`:~/kripto-bot/reset_stats.py"

# Upload updated source files (Executor & Settings)
scp -i $Key -o StrictHostKeyChecking=no src/execution/executor.py "$User@$IP`:~/kripto-bot/src/execution/executor.py"
scp -i $Key -o StrictHostKeyChecking=no config/settings.py "$User@$IP`:~/kripto-bot/config/settings.py"

$Script = @'
    # Restart the bot to apply changes
    cd ~/kripto-bot
    sudo docker-compose restart bot-live
'@


# Run it
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
