# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    sudo docker logs --tail 200 kripto-bot-live
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
