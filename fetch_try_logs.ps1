ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker-compose logs --tail 200 bot-live | grep -E 'TRY|Cüzdan|Dönüştürme|Wallet|Bakiye'"
