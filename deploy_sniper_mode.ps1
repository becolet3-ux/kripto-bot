
echo "Uploading updated main.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/main.py ubuntu@3.67.98.132:~/kripto-bot/src/

echo "Uploading updated analyzer.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/analyzer.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/

echo "Uploading updated executor.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/execution/executor.py ubuntu@3.67.98.132:~/kripto-bot/src/execution/

echo "Uploading updated opportunity_manager.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/opportunity_manager.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/

echo "Uploading updated sentiment/analyzer.py..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/sentiment/analyzer.py ubuntu@3.67.98.132:~/kripto-bot/src/sentiment/

echo "Copying to container..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker cp src/main.py kripto-bot-live:/app/src/ && sudo docker cp src/strategies/analyzer.py kripto-bot-live:/app/src/strategies/ && sudo docker cp src/execution/executor.py kripto-bot-live:/app/src/execution/ && sudo docker cp src/strategies/opportunity_manager.py kripto-bot-live:/app/src/strategies/ && sudo docker cp src/sentiment/analyzer.py kripto-bot-live:/app/src/sentiment/"

echo "Restarting bot to apply changes..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker restart kripto-bot-live"

echo "Waiting for bot to initialize..."
Start-Sleep -Seconds 10

echo "Checking logs for Sniper Mode logic..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker logs --tail 50 kripto-bot-live"
