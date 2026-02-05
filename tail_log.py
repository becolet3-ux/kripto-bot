
try:
    with open('data/bot_activity.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(''.join(lines[-20:]))
except Exception as e:
    print(e)
