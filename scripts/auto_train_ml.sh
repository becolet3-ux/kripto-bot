#!/bin/bash

# Configuration
PROJECT_DIR="/home/ubuntu/kripto-bot"
LOG_FILE="$PROJECT_DIR/data/auto_train.log"

echo "==================================================" >> $LOG_FILE
echo "Auto Training Started: $(date)" >> $LOG_FILE

# 1. Run Training Script inside Docker container
# Using 'bot-live' container which has all dependencies
echo "Running training script..." >> $LOG_FILE
sudo docker exec kripto-bot-live python src/train_models.py >> $LOG_FILE 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Training completed successfully." >> $LOG_FILE
    
    # 2. Move new model to data directory (which is volume mounted)
    # The training script saves to /app/models/ inside container
    # We move it to /app/data/models/ so it persists and is detected by Hot Reload
    
    echo "Updating model files..." >> $LOG_FILE
    sudo docker exec kripto-bot-live bash -c "mkdir -p /app/data/models && cp /app/models/*.pkl /app/data/models/ 2>/dev/null || true" >> $LOG_FILE 2>&1
    
    # 3. NO RESTART NEEDED - Hot Reload is active
    # The bot (EnsembleManager) checks file modification times every minute
    # and will reload the models automatically.
    
    # echo "Restarting bot to load new models..." >> $LOG_FILE
    # sudo docker-compose restart bot-live >> $LOG_FILE 2>&1
    
    echo "Models updated. Hot reload should pick them up." >> $LOG_FILE

else
    echo "Training FAILED. Exit code: $EXIT_CODE" >> $LOG_FILE
fi

echo "Finished: $(date)" >> $LOG_FILE
echo "==================================================" >> $LOG_FILE
