# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    # Fetch last 100 logs
    sudo docker logs --tail 100 kripto-bot-live
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
