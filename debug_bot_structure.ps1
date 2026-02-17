# Define Connection Variables
$Key = "kripto-bot-eu.pem"
$IP = "3.67.98.132"
$User = "ubuntu"

Write-Host "Debugging Bot Structure..."

ssh -i $Key -o StrictHostKeyChecking=no "$User@$IP" @"
    echo '--- Server File Structure ---'
    ls -la ~/kripto-bot
    ls -la ~/kripto-bot/config || echo 'Config folder not found on host'
    echo ''
    
    echo '--- Container File Structure (Image Content) ---'
    # Use the image built by docker-compose, name might vary, check docker images first
    IMAGE_NAME=\$(sudo docker images --format "{{.Repository}}" | grep bot-live | head -n 1)
    if [ -z "\$IMAGE_NAME" ]; then
        echo "Image not found, listing all images:"
        sudo docker images
    else
        echo "Inspecting image: \$IMAGE_NAME"
        sudo docker run --rm --entrypoint /bin/bash \$IMAGE_NAME -c "ls -la /app && ls -la /app/config || echo 'Config folder not found in container'"
    fi
"@
