import json
import os
import time
from typing import Dict, Any

class StateManager:
    def __init__(self, filepath: str = "data/bot_state.json", stats_filepath: str = "data/bot_stats.json"):
        self.filepath = filepath
        self.stats_filepath = stats_filepath
        self.ensure_dir()

    def ensure_dir(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        os.makedirs(os.path.dirname(self.stats_filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            self.save_state({})
        if not os.path.exists(self.stats_filepath):
            self.save_stats({})

    def save_state(self, data: Dict[str, Any]):
        try:
            # Add timestamp to state
            data['last_updated'] = time.time()
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"❌ Failed to save state: {e}")

    def load_state(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.filepath):
                return {}
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load state: {e}")
            return {}

    def save_stats(self, stats: Dict[str, Any]):
        try:
            stats['last_updated'] = time.time()
            with open(self.stats_filepath, 'w') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"❌ Failed to save stats: {e}")

    def load_stats(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.stats_filepath):
                return {}
            with open(self.stats_filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load stats: {e}")
            return {}
