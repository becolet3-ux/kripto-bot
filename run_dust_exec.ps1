
echo "Uploading updated executor.py to remote server..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no src/execution/executor.py ubuntu@3.67.98.132:~/kripto-bot/src/execution/

echo "Uploading run_dust_conversion.py to remote server..."
scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no run_dust_conversion.py ubuntu@3.67.98.132:~/kripto-bot/

echo "Copying updated executor code to container..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker cp src/execution/executor.py kripto-bot-live:/app/src/execution/"

echo "Copying script to container..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker cp run_dust_conversion.py kripto-bot-live:/app/"

echo "Executing script..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker exec kripto-bot-live python run_dust_conversion.py"
