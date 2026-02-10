tar -czf src.tar.gz src scripts
scp -i "kripto-bot-eu.pem" -o StrictHostKeyChecking=no src.tar.gz ubuntu@3.67.98.132:/home/ubuntu/kripto-bot/
ssh -i "kripto-bot-eu.pem" -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd /home/ubuntu/kripto-bot && tar -xzf src.tar.gz && sudo docker-compose up -d --build"