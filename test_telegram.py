import requests
import os
import sys

# Load env variables (simple parser for this test)
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

TOKEN = env_vars.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = env_vars.get('TELEGRAM_CHAT_ID')

if not TOKEN or not CHAT_ID:
    print("Error: Missing credentials in .env")
    sys.exit(1)

def send_test_message():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🚀 *KriptoBot Test Mesajı*\n\nTelegram bildirimleri başarıyla yapılandırıldı! Artık işlem sinyallerini buradan alacaksınız.",
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

send_test_message()
