# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "🔄 Rebuilding Dashboard Container..."

$Script = @"
    cd ~/kripto-bot
    echo "🛑 Stopping dashboard..."
    sudo docker-compose stop dashboard-live
    
    echo "🏗️ Rebuilding dashboard..."
    sudo docker-compose up -d --build dashboard-live
    
    echo "✅ Done! Checking dashboard logs..."
    sleep 5
    sudo docker-compose logs --tail=20 dashboard-live
"@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
