import json
import os

try:
    with open('kripto-bot/data/bot_state_paper.json') as f:
        d = json.load(f)
        positions = d.get('paper_positions', {})
        print('Keys:', list(positions.keys()))
        for k, v in positions.items():
            print(f'{k}: Qty={v.get("quantity")}, Entry={v.get("entry_price")}')
except Exception as e:
    print(e)
