import logging
import os
import time
import requests
from config.settings import settings
from src.database import DatabaseHandler

class BotLogger:
    def __init__(self, log_file="data/bot_activity.log"):
        self.log_file = log_file
        self.ensure_dir()
        self.setup_logger()
        # Initialize Database Handler
        try:
            self.db = DatabaseHandler()
        except Exception as e:
            print(f"Failed to init DB in logger: {e}")
            self.db = None

        # Alerting Configuration
        self.tg_token = settings.TELEGRAM_BOT_TOKEN
        self.tg_chat_id = settings.TELEGRAM_CHAT_ID
        self.last_alert_time = 0
        self.alert_cooldown = 60 # Seconds between identical alerts to avoid spam

    def ensure_dir(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def setup_logger(self):
        # Configure logging to write to file and console
        self.logger = logging.getLogger("KriptoBot")
        self.logger.setLevel(logging.INFO)
        
        # Avoid adding handlers multiple times
        if not self.logger.handlers:
            # File Handler
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # Console Handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def send_telegram_alert(self, message):
        """Sends a message to the configured Telegram chat."""
        if not self.tg_token or not self.tg_chat_id:
            return

        # Simple cooldown mechanism
        if time.time() - self.last_alert_time < 2: 
            return # Avoid hammering API

        try:
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            payload = {
                "chat_id": self.tg_chat_id,
                "text": f"🤖 KriptoBot Alert:\n\n{message}",
                "parse_mode": "Markdown"
            }
            # Timeout to prevent hanging
            requests.post(url, json=payload, timeout=5)
            self.last_alert_time = time.time()
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")

    def log(self, message):
        self.logger.info(message)
        
        # Determine Log Level & Trigger Alerts
        level = "INFO"
        is_alert = False
        
        if "ERROR" in message or "❌" in message or "Critical" in message:
            level = "ERROR"
            is_alert = True
        elif "WARNING" in message or "⚠️" in message:
            level = "WARNING"
            if "Daily Loss" in message or "Stop Loss" in message:
                is_alert = True
        elif "✅" in message and ("ENTRY" in message or "EXIT" in message):
            level = "SUCCESS"
            # Optional: Alert on Trades too? Let's say yes for now as it's useful.
            is_alert = True
        elif "🚀" in message: # Real trade execution
            level = "SUCCESS"
            is_alert = True

        # Also log to Database
        if self.db:
            try:
                self.db.log_message(level, message)
            except Exception:
                pass # Fail silently

        # Send Telegram Alert if critical
        if is_alert:
            self.send_telegram_alert(message)

# Global Logger Instance
logger = BotLogger()

def log(message):
    logger.log(message)
