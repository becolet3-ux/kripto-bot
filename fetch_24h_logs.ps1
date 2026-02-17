
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

# Logları çekip lokale kaydet
$cmd = "cd kripto-bot && sudo docker-compose logs --tail=5000 bot-live"

# Dosyayı lokale yaz
$logs = ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $cmd
$logs | Out-File -Encoding utf8 "last_24h_logs.txt"
