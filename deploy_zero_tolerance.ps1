echo "Deploying Zero Tolerance Updates to 3.67.98.132..."

# Config
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no config/settings.py ubuntu@3.67.98.132:~/kripto-bot/config/settings.py

# Strategies
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/strategy_manager.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/strategy_manager.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/funding_aware_strategy.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/funding_aware_strategy.py
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/analyzer.py ubuntu@3.67.98.132:~/kripto-bot/src/strategies/analyzer.py

# Docker Update & Restart
echo "Updating Docker Container and Restarting..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker cp ~/kripto-bot/config/settings.py kripto-bot-live:/app/config/settings.py && sudo docker cp ~/kripto-bot/src/strategies/strategy_manager.py kripto-bot-live:/app/src/strategies/strategy_manager.py && sudo docker cp ~/kripto-bot/src/strategies/funding_aware_strategy.py kripto-bot-live:/app/src/strategies/funding_aware_strategy.py && sudo docker cp ~/kripto-bot/src/strategies/analyzer.py kripto-bot-live:/app/src/strategies/analyzer.py && sudo docker restart kripto-bot-live"

echo "Deployment DONE."
