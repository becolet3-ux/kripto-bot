import json
import os

state_file = 'data/bot_state.json'

if os.path.exists(state_file):
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clear positions and history
        print(f"Cleaning {len(data.get('paper_positions', {}))} positions...")
        data['paper_positions'] = {}
        data['order_history'] = []
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
        print("✅ State cleaned successfully.")
    except Exception as e:
        print(f"❌ Error cleaning state: {e}")
else:
    print("State file not found.")