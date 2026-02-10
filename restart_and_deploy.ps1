
echo "Uploading updated main.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/main.py ubuntu@3.67.98.132:~/kripto-bot/src/

echo "Uploading updated analyzer.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/analyzer.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/

echo "Uploading updated executor.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/execution/executor.py ubuntu@3.67.98.132:~/kripto-bot/src/execution/

echo "Starting bot-live container..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker-compose up -d bot-live"

echo "Waiting for initialization..."
Start-Sleep -Seconds 10

echo "Checking logs..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker logs --tail 50 kripto-bot-live"
