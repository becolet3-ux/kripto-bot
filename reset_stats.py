import json
import os
import shutil

# Path to stats file
STATS_FILE = '/home/ubuntu/kripto-bot/data/bot_stats_live.json'
STATE_FILE = '/home/ubuntu/kripto-bot/data/bot_state_live.json'

def reset_file(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Create backup
    shutil.copy(file_path, file_path + '.bak')

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Handle different structures
        target = None
        if 'stats' in data:
             target = data['stats']
        elif 'paper_positions' in data: 
             # Likely bot_state_live.json which should have 'stats' key
             if 'stats' not in data:
                 data['stats'] = {}
             target = data['stats']
        else:
             # Likely bot_stats_live.json which IS the stats dict
             target = data
        
        # Current stats
        print(f"File: {file_path}")
        print(f"Old Start Balance: {target.get('daily_start_balance', 'N/A')}")
        print(f"Old Realized PnL: {target.get('daily_realized_pnl', 'N/A')}")

        # Reset logic: Set start balance to current balance from logs (approx 5.59)
        # We set it slightly lower to avoid immediate trigger if market dips
        target['daily_start_balance'] = 5.50 
        target['daily_realized_pnl'] = 0.0
        target['daily_trade_count'] = 0
        
        # Save back
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
            
        print(f"New Start Balance: {target.get('daily_start_balance', 'N/A')}")
        print("Stats reset successfully.\n")
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")

# Reset both files
reset_file(STATS_FILE)
reset_file(STATE_FILE)
