$files = @(
    "src/execution/executor.py"
)

foreach ($file in $files) {
    echo "Uploading $file..."
    scp -i kripto-bot-eu.pem -o StrictHostKeyChecking=no $file ubuntu@3.67.98.132:kripto-bot/$file
}

echo "Restarting Live Bot..."
ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "cd kripto-bot && sudo docker-compose restart bot-live"

echo "Deployment Complete."
