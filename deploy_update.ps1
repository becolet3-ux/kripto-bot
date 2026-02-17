
echo "Deploying updates to Docker container..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/analyzer.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/analyzer.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/opportunity_manager.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/opportunity_manager.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/execution/executor.py ubuntu@3.67.98.132:~/kripto-bot/src/execution/executor.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/execution/trade_manager.py ubuntu@3.67.98.132:~/kripto-bot/src/execution/trade_manager.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/collectors/binance_loader.py ubuntu@3.67.98.132:~/kripto-bot/src/collectors/binance_loader.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no config/settings.py ubuntu@3.67.98.132:~/kripto-bot/config/settings.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/main.py ubuntu@3.67.98.132:~/kripto-bot/src/main.py

ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker cp ~/kripto-bot/src/strategies/analyzer.py kripto-bot-live:/app/src/strategies/analyzer.py && sudo docker cp ~/kripto-bot/src/strategies/opportunity_manager.py kripto-bot-live:/app/src/strategies/opportunity_manager.py && sudo docker cp ~/kripto-bot/src/execution/executor.py kripto-bot-live:/app/src/execution/executor.py && sudo docker cp ~/kripto-bot/src/execution/trade_manager.py kripto-bot-live:/app/src/execution/trade_manager.py && sudo docker cp ~/kripto-bot/src/collectors/binance_loader.py kripto-bot-live:/app/src/collectors/binance_loader.py && sudo docker cp ~/kripto-bot/config/settings.py kripto-bot-live:/app/config/settings.py && sudo docker cp ~/kripto-bot/src/main.py kripto-bot-live:/app/src/main.py && sudo docker restart kripto-bot-live"
echo "Deployment complete. Bot restarted."
