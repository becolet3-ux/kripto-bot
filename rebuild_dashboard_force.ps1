# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- Checking Requirements File Content ---"
    cat requirements_dashboard.txt
    
    echo "--- Stopping Dashboard ---"
    sudo docker-compose stop dashboard-live
    
    echo "--- Pruning Docker System ---"
    sudo docker system prune -f
    
    echo "--- Rebuilding Dashboard No Cache ---"
    # Force rebuild without cache to ensure new requirements are installed
    sudo docker-compose build --no-cache dashboard-live
    
    echo "--- Starting Dashboard ---"
    sudo docker-compose up -d dashboard-live
    
    echo "--- Checking Logs ---"
    sleep 10
    sudo docker-compose logs --tail=50 dashboard-live
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
