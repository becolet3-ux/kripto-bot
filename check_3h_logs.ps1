
$User = "ubuntu"
$IP = "3.67.98.132"
$Key = "c:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"

# Script content to run on server
$Script = @'
echo "=== CRITICAL EVENTS LAST 3 HOURS ==="
# Get logs from last 3 hours, filter for key events
sudo docker logs --since 3h kripto-bot-live 2>&1 | grep -E "ERROR|WARNING|ENTRY|EXIT|FILLED|Signal Detected|Bakiye|Pozisyon|Zarar" | tail -n 50

echo ""
echo "=== LATEST STATUS (Last 50 Lines) ==="
sudo docker logs --tail 50 kripto-bot-live 2>&1
'@

# Execute via SSH using pipe to avoid quoting issues
$Script | ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "bash -s"
