$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Debugging Remote Execution..."

# 1. Check if file exists in the mounted directory on host
Write-Host "1. Checking file on host..."
ssh -i $pem $opts $ip "ls -l ~/kripto-bot/src/check_ml_env.py"

# 2. Check if file exists inside container
Write-Host "2. Checking file inside container..."
ssh -i $pem $opts $ip "sudo docker-compose exec -T bot-live ls -l /app/src/check_ml_env.py"

# 3. Simple Echo Test
Write-Host "3. Echo Test..."
ssh -i $pem $opts $ip "sudo docker-compose exec -T bot-live echo 'Hello from Container'"

# 4. Run Python with explicit path
Write-Host "4. Running Python..."
ssh -i $pem $opts $ip "sudo docker-compose exec -T bot-live python /app/src/check_ml_env.py"
