
$User = "ubuntu"
$IP = "3.67.98.132"
$Key = "c:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"

# Script content to run on server
$Script = @'
echo "=== SERVER HEALTH ==="
echo "--- Uptime ---"
uptime
echo ""
echo "--- CPU Usage ---"
top -bn1 | grep "Cpu(s)"
echo ""
echo "--- Memory Usage ---"
free -h
echo ""
echo "--- Disk Usage ---"
df -h | grep "/dev/root"
echo ""

echo "=== BOT CONTAINER STATS ==="
# Get stats for the bot container
sudo docker stats kripto-bot-live --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
'@

# Execute via SSH
$Script | ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "bash -s"
