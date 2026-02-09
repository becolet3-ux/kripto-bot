$Key = "C:\Users\emdam\Documents\trae_projects\kripto-bot\kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Analyzing Space..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h && echo '--- /var ---' && sudo du -sh /var/* | sort -hr | head -n 5 && echo '--- /home ---' && sudo du -sh /home/ubuntu/* | sort -hr | head -n 5"

Write-Host "Deep Cleanup..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "sudo journalctl --vacuum-time=1s && sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/* && rm -rf ~/.cache/pip && sudo docker system prune -a -f --volumes"

Write-Host "Space After Cleanup..."
ssh -i $Key -o StrictHostKeyChecking=no $User@$IP "df -h"
