
echo "Fetching WIF logs..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker logs kripto-bot-live 2>&1 | grep 'WIF/USDT' | tail -n 20"
