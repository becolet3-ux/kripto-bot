param(
    [int]$Tail = 200,
    [int]$SinceHours = 0
)

if ($SinceHours -gt 0) {
    Write-Output "Fetching logs from last $SinceHours hour(s) from kripto-bot-live..."
    ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker logs --since=${SinceHours}h kripto-bot-live"
} else {
    Write-Output "Fetching last $Tail lines from kripto-bot-live logs..."
    ssh -i kripto-bot-eu.pem -o StrictHostKeyChecking=no ubuntu@3.67.98.132 "sudo docker logs --tail=$Tail kripto-bot-live"
}

Write-Output "Done."
