echo "Setting live mode in host .env and restarting container..."

ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "
  set -e
  if [ -f /home/ubuntu/kripto-bot/.env ]; then
    sed -i 's/^USE_MOCK_DATA=.*/USE_MOCK_DATA=False/' /home/ubuntu/kripto-bot/.env || true
    sed -i 's/^LIVE_TRADING=.*/LIVE_TRADING=True/' /home/ubuntu/kripto-bot/.env || true
    grep -q '^USE_MOCK_DATA=' /home/ubuntu/kripto-bot/.env || echo USE_MOCK_DATA=False >> /home/ubuntu/kripto-bot/.env
    grep -q '^LIVE_TRADING=' /home/ubuntu/kripto-bot/.env || echo LIVE_TRADING=True >> /home/ubuntu/kripto-bot/.env
  else
    echo USE_MOCK_DATA=False > /home/ubuntu/kripto-bot/.env
    echo LIVE_TRADING=True >> /home/ubuntu/kripto-bot/.env
  fi
  sudo docker restart kripto-bot-live
"

echo "Host .env updated and container restarted."
