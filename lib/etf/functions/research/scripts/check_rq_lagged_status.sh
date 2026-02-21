#!/bin/bash
# Monitor RQ lagged backtest progress

LOG_FILE="/tmp/rq_factor_lagged_backtest.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    exit 1
fi

echo "=== RQ Lagged Backtest Status ==="
echo ""

# Check if process is still running
if pgrep -f "backtest_rq_factor_lagged.py" > /dev/null; then
    echo "Status: RUNNING"
else
    echo "Status: COMPLETE (or not running)"
fi

echo ""
echo "=== Recent Log Output (last 30 lines) ==="
tail -30 "$LOG_FILE"

echo ""
echo "=== Progress Indicators ==="
grep -E "(Processing|Backtest complete|Performance Metrics)" "$LOG_FILE" | tail -10

echo ""
echo "=== Errors/Warnings (if any) ==="
grep -E "(ERROR|WARNING|Error|Exception)" "$LOG_FILE" | tail -5

