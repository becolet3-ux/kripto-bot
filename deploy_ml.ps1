$pem = "kripto-bot-eu.pem"
$ip = "ubuntu@3.67.98.132"
$opts = "-o StrictHostKeyChecking=no"

Write-Host "Stopping containers..."
ssh -i $pem $opts $ip "cd kripto-bot && sudo docker-compose down"

Write-Host "Updating code and rebuilding with ML libraries..."
# We need to make sure the server pulls the latest changes if we were using git, 
# but since we are uploading files directly via scp (or similar in a real scenario), 
# here we assume the local files are the source of truth and we need to sync them.
# However, I don't have an SCP tool here. 
# Wait, I am simulating the environment. In this environment, I am editing local files.
# I need to 'upload' them to the remote server. 
# Since I can't use SCP/RSYNC directly easily, I will use a trick: 
# I will read the content of the files and write them to the remote server using SSH and cat.

# 1. Update requirements.txt
$req_content = Get-Content -Raw c:\Users\emdam\Documents\trae_projects\kripto-bot\requirements.txt
$req_content = $req_content -replace "`r", "" # Fix line endings for Linux
$req_b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($req_content))
ssh -i $pem $opts $ip "echo $req_b64 | base64 -d > ~/kripto-bot/requirements.txt"

# 2. Update docker-compose.yml
$dc_content = Get-Content -Raw c:\Users\emdam\Documents\trae_projects\kripto-bot\docker-compose.yml
$dc_content = $dc_content -replace "`r", ""
$dc_b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($dc_content))
ssh -i $pem $opts $ip "echo $dc_b64 | base64 -d > ~/kripto-bot/docker-compose.yml"

Write-Host "Building and Starting Bot with ML Support (This may take a while)..."
ssh -i $pem $opts $ip "cd kripto-bot && sudo docker-compose up -d --build bot-live dashboard-live"

Write-Host "Checking logs..."
Start-Sleep -Seconds 10
ssh -i $pem $opts $ip "sudo docker logs --tail 50 kripto-bot-live"

Write-Host "Done!"
