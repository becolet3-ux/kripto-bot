$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Fetching Logs from File (data/bot_activity_live.log) on Server ($IP)...`n"

# Remote Execution: Tail the log file directly
$commands = @(
    "cd kripto-bot",
    "echo '================ LIVE BOT LOG FILE (Last 500 lines) ================'",
    "tail -n 500 data/bot_activity_live.log",
    "echo ' '",
    "echo '================ CHECKING LOGS DIR ================'",
    "ls -l logs/ 2>/dev/null || echo 'No logs dir content'"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand > logs_file_check.txt
Write-Host "Logs saved to logs_file_check.txt"