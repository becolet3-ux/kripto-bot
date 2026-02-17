echo "Redeploying analyzer.py to container..."

# Upload to a neutral path to avoid permission issues
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/strategies/analyzer.py ubuntu@3.67.98.132:~/analyzer.py

# Copy into container and restart
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker cp ~/analyzer.py kripto-bot-live:/app/src/strategies/analyzer.py && sudo docker restart kripto-bot-live"

echo "Redeploy complete."
