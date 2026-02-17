
$User = "ubuntu"
$IP = "3.67.98.132"
$Key = "c:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"

# Script content to run on server
$Script = @'
echo "=== LATEST LOGS ==="
# Fetch last 100 lines to ensure we see the result of Sniper Entry
sudo docker logs --tail 100 kripto-bot-live

echo ""
echo "=== ACTIVE POSITIONS ==="
# Read the state file
cat ~/kripto-bot/data/bot_state_live.json
'@

# Execute via SSH
$Script | ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "bash -s"
