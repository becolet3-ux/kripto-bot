import json

try:
    with open('data/bot_state.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    commentary = data.get('commentary', {})
    print("Commentary Keys:", commentary.keys())
    print("Commentary Content (Preview):", str(commentary)[:500])
except Exception as e:
    print(f"Error: {e}")
