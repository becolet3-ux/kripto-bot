
import re

log_file = "server_logs_large.txt"
pattern = re.compile(r"EXIT|SELL|STOP_LOSS|PROFIT|RISK|Loss|Win|Order|Filled|Exec|Sold|Bought")

matches = []
try:
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if pattern.search(line):
                matches.append(line.strip())
except Exception as e:
    print(f"Error: {e}")

print(f"Found {len(matches)} matches.")
for line in matches[-50:]:
    print(line)
