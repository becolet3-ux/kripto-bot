
$pem = "kripto-bot-eu.pem"
$host_ip = "ubuntu@3.67.98.132"
$remote_dir = "/home/ubuntu/kripto-bot"

# 1. Dump logs to file on server (Large)
Write-Host "Dumping logs on server..."
ssh -i $pem -o StrictHostKeyChecking=no $host_ip "cd $remote_dir && sudo docker-compose logs --tail=10000 bot-live > bot_logs_large.txt"

# 2. Download logs
Write-Host "Downloading logs..."
scp -i $pem -o StrictHostKeyChecking=no "$host_ip`:$remote_dir/bot_logs_large.txt" ./server_logs_large.txt

Write-Host "Done."
