# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    python3 ~/kripto-bot/analyze_state.py
'@

# Upload the python script first
scp -i $Key -o StrictHostKeyChecking=no analyze_state.py "$User@$IP`:~/kripto-bot/analyze_state.py"


# Run it
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
