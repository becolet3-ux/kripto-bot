from config.settings import settings
import os

print(f"IS_TR_BINANCE from settings: {settings.IS_TR_BINANCE}")
print(f"LIVE_TRADING from settings: {settings.LIVE_TRADING}")
print(f"MAX_POSITION_SIZE_USD from settings: {settings.MAX_POSITION_SIZE_USD}")
print(f"USE_MOCK_DATA from settings: {settings.USE_MOCK_DATA}")

print("--- ENV VARS ---")
print(f"IS_TR_BINANCE env: {os.environ.get('IS_TR_BINANCE')}")
