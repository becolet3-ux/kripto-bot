echo "Setting live mode in container .env..."

ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "
 set -e
 sudo docker stop kripto-bot-live || true
 if sudo docker cp kripto-bot-live:/app/.env /home/ubuntu/.env.tmp 2>/dev/null; then
   sed -i 's/^USE_MOCK_DATA=.*/USE_MOCK_DATA=False/' /home/ubuntu/.env.tmp || true
   sed -i 's/^LIVE_TRADING=.*/LIVE_TRADING=True/' /home/ubuntu/.env.tmp || true
   grep -q '^USE_MOCK_DATA=' /home/ubuntu/.env.tmp || echo USE_MOCK_DATA=False >> /home/ubuntu/.env.tmp
   grep -q '^LIVE_TRADING=' /home/ubuntu/.env.tmp || echo LIVE_TRADING=True >> /home/ubuntu/.env.tmp
 else
   echo USE_MOCK_DATA=False > /home/ubuntu/.env.tmp
   echo LIVE_TRADING=True >> /home/ubuntu/.env.tmp
 fi
 sudo docker cp /home/ubuntu/.env.tmp kripto-bot-live:/app/.env
 sudo docker start kripto-bot-live
"

echo "Live mode set and container restarted."
