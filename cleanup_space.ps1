$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Freeing up Disk Space on Remote Server...`n"

$commands = @(
    "echo '--- Disk Usage Before ---'",
    "df -h /",
    "echo '--- Pruning Docker System (All unused images/containers) ---'",
    "sudo docker system prune -a -f",
    "echo '--- Cleaning Apt Cache ---'",
    "sudo apt-get clean",
    "echo '--- Removing Temp Files ---'",
    "rm -rf ~/.cache",
    "rm -f ~/kripto-bot/src.tar.gz ~/kripto-bot/src.zip",
    "echo '--- Disk Usage After ---'",
    "df -h /"
)

$remoteCommand = $commands -join " && "

ssh -i $Key -o StrictHostKeyChecking=no $User@$IP $remoteCommand
Write-Host "`nCleanup Completed."