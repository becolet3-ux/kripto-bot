from config.settings import settings
import sys

def check_keys():
    print("--- API Key Check ---")
    
    api_key = settings.BINANCE_API_KEY
    secret_key = settings.BINANCE_SECRET_KEY
    
    if not api_key:
        print("❌ BINANCE_API_KEY is Missing or Empty!")
    else:
        print(f"✅ BINANCE_API_KEY found (Length: {len(api_key)})")
        if " " in api_key:
            print("   ⚠️ WARNING: API Key contains spaces!")
        if len(api_key) != 64:
            print(f"   ⚠️ WARNING: API Key length is usually 64 chars, yours is {len(api_key)}.")
        if api_key.startswith("your_"):
            print("   ❌ ERROR: You still have the default placeholder 'your_api_key'!")

    if not secret_key:
        print("❌ BINANCE_SECRET_KEY is Missing or Empty!")
    else:
        print(f"✅ BINANCE_SECRET_KEY found (Length: {len(secret_key)})")
        if " " in secret_key:
            print("   ⚠️ WARNING: Secret Key contains spaces!")
        if len(secret_key) != 64:
            print(f"   ⚠️ WARNING: Secret Key length is usually 64 chars, yours is {len(secret_key)}.")
        if secret_key.startswith("your_"):
            print("   ❌ ERROR: You still have the default placeholder 'your_secret_key'!")

    print("\n--- .env File Content (First 2 chars hidden) ---")
    try:
        with open(".env", "r") as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    # Mask value
                    masked = val[:2] + "*" * (len(val)-4) + val[-2:] if len(val) > 4 else "****"
                    print(f"{key}={masked}")
    except Exception as e:
        print(f"Could not read .env file directly: {e}")

if __name__ == "__main__":
    check_keys()
