# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Updating .env with Correct Chat ID ---"
    
    # Update TELEGRAM_CHAT_ID
    if grep -q "TELEGRAM_CHAT_ID=" .env; then
        sed -i 's|TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=1690495566|g' .env
    else
        echo "TELEGRAM_CHAT_ID=1690495566" >> .env
    fi

    echo "--- Restarting Bot to Apply Changes ---"
    sudo docker-compose restart bot-live
    
    echo "--- Verifying Restart ---"
    sleep 5
    sudo docker-compose logs --tail=20 bot-live
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
