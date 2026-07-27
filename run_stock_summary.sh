#!/bin/zsh
cd /Users/shin/stock/mystock-tracker || exit 1

LOG=logs/run.log

echo "=== Run started: $(date) ===" >> "$LOG"
.venv/bin/python3 stock_summary.py >> "$LOG" 2>&1
STATUS=$?
echo "=== Run finished: $(date) exit=$STATUS ===" >> "$LOG"

exit $STATUS
