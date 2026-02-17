# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    sudo docker logs --tail 2000 kripto-bot-live > last_logs.txt
    cat last_logs.txt
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
