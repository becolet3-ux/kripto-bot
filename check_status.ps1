echo "=== LIVE BOT LOGS ==="
ssh -i kripto-bot.pem -o StrictHostKeyChecking=no ubuntu@63.180.55.81 "sudo docker logs kripto-bot-live --tail 200"
echo "`n=== PAPER BOT LOGS ==="
ssh -i kripto-bot.pem -o StrictHostKeyChecking=no ubuntu@63.180.55.81 "sudo docker logs kripto-bot-paper --tail 200"