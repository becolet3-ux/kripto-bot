# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    # Restart the bot to apply changes
    cd ~/kripto-bot
    sudo docker-compose restart bot-live
'@

# Upload the modified file
scp -i $Key -o StrictHostKeyChecking=no src/execution/executor.py "$User@$IP`:~/kripto-bot/src/execution/executor.py"


# Restart
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
