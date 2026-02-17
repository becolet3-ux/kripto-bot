# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"
$RemotePath = "/home/ubuntu/kripto-bot"

# 1. Run standard deployment to upload files
Write-Host "🚀 Uploading files..."
./deploy_full_zip.ps1

# 2. Force Clean Restart on Server
Write-Host "🔄 Forcing Clean Restart on Server..."

$ScriptBlock = @"
    cd $RemotePath
    echo "🛑 Stopping containers..."
    sudo docker-compose down
    
    echo "🧹 Cleaning up pycache..."
    sudo find . -name "__pycache__" -type d -exec rm -rf {} +
    
    echo "🧹 Pruning docker system..."
    sudo docker system prune -f
    
    echo "🚀 Starting fresh..."
    sudo docker-compose up -d --build --force-recreate
    
    echo "✅ Done! Checking logs..."
    sleep 5
    sudo docker-compose logs --tail=20 bot-live
"@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $ScriptBlock
