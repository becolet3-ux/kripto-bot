param(
    [string]$Key = "kripto-bot-eu.pem",
    [string]$IP = "3.67.98.132",
    [string]$User = "ubuntu",
    [string]$Container = "kripto-bot-live"
)

Write-Host "Fetching last 30 minutes logs from $Container on $IP..."
ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" "sudo docker logs --since 30m $Container"
