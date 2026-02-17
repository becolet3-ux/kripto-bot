
$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
Write-Host "Performing aggressive cleanup on server..."

$cleanup_cmd = "
echo 'Cleaning Docker...'
sudo docker system prune -a -f --volumes

echo 'Cleaning Apt cache...'
sudo apt-get clean
sudo apt-get autoremove -y

echo 'Cleaning Systemd journals...'
sudo journalctl --vacuum-time=1s

echo 'Removing old archives/temp files...'
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

echo 'Checking disk usage...'
df -h
"

ssh -i $pem -o StrictHostKeyChecking=no $ip $cleanup_cmd
