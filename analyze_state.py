import json
import os
from datetime import datetime

file_path = '/home/ubuntu/kripto-bot/data/bot_state_live.json'

if not os.path.exists(file_path):
    print("State file not found")
    exit()

with open(file_path, 'r') as f:
    data = json.load(f)

print("--- Current Positions ---")
positions = data.get('paper_positions', {})
if not positions:
    print("No open positions.")
else:
    for sym, pos in positions.items():
        print(f"Symbol: {sym}, Qty: {pos.get('quantity')}, Entry: {pos.get('entry_price')}")

print("\n--- Last 5 Orders ---")
orders = data.get('order_history', [])
for order in orders[-5:]:
    ts = order.get('timestamp')
    dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{dt} - {order.get('action')} {order.get('symbol')} Price: {order.get('price')}")
