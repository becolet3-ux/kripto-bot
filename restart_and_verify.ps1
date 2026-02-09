
echo "Restarting bot (force)..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker restart kripto-bot-live"

echo "Waiting 5 seconds..."
timeout 5

echo "Checking status..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker ps"
