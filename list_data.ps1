# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

$Script = @'
    ls -R ~/kripto-bot/data
'@

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" $Script
