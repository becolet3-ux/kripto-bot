# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Running comprehensive diagnostics on the server..."

# Execute remote diagnostics via SSH
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    echo '--- 0. Basic System Info ---'
    uname -a
    uptime
    echo ''

    echo '--- 1. Testing Local Access (Curl) ---'
    if curl -s -I http://localhost:80 > /dev/null; then
        echo 'SUCCESS: Dashboard is responding locally on port 80.'
    else
        echo 'FAILURE: Dashboard is NOT responding locally on port 80.'
        curl -v http://localhost:80 2>&1 | head -n 10
    fi
    echo ''

    echo '--- 2. Checking UFW Firewall Status ---'
    sudo ufw status verbose
    echo ''

    echo '--- 3. Checking IPTables Rules for Port 80 ---'
    sudo iptables -L INPUT -n | grep 80 || echo 'No specific iptables rules found for port 80.'
    echo ''

    echo '--- 4. Checking Docker Container Logs (Last 20 lines) ---'
    cd ~/kripto-bot && sudo docker-compose logs --tail=20 dashboard-live
    echo ''

    echo '--- 5. CPU & Memory Usage (top/free) ---'
    top -b -n1 | head -n5
    echo ''
    free -h
    echo ''

    echo '--- 6. Disk Usage (df -h /) ---'
    df -h /
"@

Write-Host "`nDiagnostics completed."
