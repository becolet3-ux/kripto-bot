
cd /home/ubuntu/kripto-bot
git pull
sudo docker-compose restart bot-live
# Check logs immediately to see if it passes the stuck point
sleep 10
sudo docker logs --tail 20 kripto-bot-live
