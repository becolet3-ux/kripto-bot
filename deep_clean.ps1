$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Starting Deep Clean..."

# 1. Stop Docker again
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker-compose down 2>/dev/null"

# 2. Prune Docker again (just in case)
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo docker system prune -a -f --volumes"

# 3. Clean System Logs & Caches
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo journalctl --vacuum-time=1s"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo apt-get clean"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo rm -rf /var/lib/apt/lists/*"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo rm -rf /var/log/*.gz"
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo rm -rf /tmp/*"

# 4. Check for Snap cache (if used)
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo rm -rf /var/lib/snapd/cache/*"

# 5. Check Disk Space and Largest Directories
Write-Host "Checking Disk Space..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h"
Write-Host "Checking Largest Directories..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo du -h --max-depth=1 / | sort -hr | head -n 10"
Write-Host "Checking Kripto-Bot Directory Size..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "du -sh ~/kripto-bot"
