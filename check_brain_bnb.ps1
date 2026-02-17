
$User = "ubuntu"
$IP = "3.67.98.132"
$Key = "c:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"

# Script content to run on server
$Script = @'
echo "=== RECENT BRAIN PLAN & BNB LOGS ==="
# Search for Brain Plan or BNB score messages in recent logs
sudo docker logs --since 3h kripto-bot-live 2>&1 | grep -iE "Brain Plan|BNB|Score:" | tail -n 50

echo ""
echo "=== CURRENT BRAIN PLAN STATE ==="
# Extract the "brain_plan" section from the state file
cat ~/kripto-bot/data/bot_state_live.json | grep -A 20 "brain_plan"
'@

# Execute via SSH
$Script | ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "bash -s"
