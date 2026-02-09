
echo "Uploading updated main.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/main.py ubuntu@3.67.98.132:~/kripto-bot/src/

echo "Uploading updated executor.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/execution/executor.py ubuntu@3.67.98.132:~/kripto-bot/src/execution/

echo "Copying to container..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker cp src/main.py kripto-bot-live:/app/src/ && sudo docker cp src/execution/executor.py kripto-bot-live:/app/src/execution/"

echo "Restarting bot to apply changes..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker restart kripto-bot-live"

echo "Checking logs for Sniper Mode logic..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker logs --tail 50 kripto-bot-live"
