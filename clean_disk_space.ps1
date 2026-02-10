
echo "Cleaning up disk space on server..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker system prune -af && sudo journalctl --vacuum-time=1s && sudo rm -rf /var/log/*.gz"

echo "Checking disk usage..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "df -h"
