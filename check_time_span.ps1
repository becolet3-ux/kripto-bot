# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    cd ~/kripto-bot
    echo "--- First Data Point ---"
    sed -n '2p' data/ml_training_data.csv
    echo "--- Last Data Point ---"
    tail -n 1 data/ml_training_data.csv
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
