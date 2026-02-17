import requests
import sys

TOKEN = "8592801326:AAFtsR_NedSesy1JH4sxxTDCn6yEN8KpyU4"
USERNAME = "emregor"

def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            print(f"Error: {data}")
            return None
            
        for result in data["result"]:
            if "message" in result:
                chat = result["message"]["chat"]
                if chat.get("username") == USERNAME or chat.get("type") == "private":
                    # If username matches or it's a private message (likely from the user)
                    # We prefer matching username if possible
                    if chat.get("username") == USERNAME:
                        return chat["id"]
                    
        # If no exact username match, return the last private chat id
        for result in reversed(data["result"]):
             if "message" in result and result["message"]["chat"]["type"] == "private":
                 return result["message"]["chat"]["id"]
                 
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

chat_id = get_chat_id()
if chat_id:
    print(f"FOUND_CHAT_ID={chat_id}")
else:
    print("CHAT_ID_NOT_FOUND")
