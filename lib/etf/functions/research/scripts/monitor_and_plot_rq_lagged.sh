#!/bin/bash
# Monitor RQ lagged backtest and plot when complete

LOG_FILE="/tmp/rq_factor_lagged_backtest.log"
OUTPUT_DIR="data/research/sp500_backtest"
MAX_WAIT_HOURS=6  # Maximum time to wait (6 hours)
CHECK_INTERVAL=300  # Check every 5 minutes

echo "=== Monitoring RQ Lagged Backtest ==="
echo "Will check every 5 minutes and plot when complete"
echo ""

start_time=$(date +%s)
max_wait_seconds=$((MAX_WAIT_HOURS * 3600))

while true; do
    # Check if all result files exist
    lag1_file="${OUTPUT_DIR}/rq_factor_lag1_backtest_results.csv"
    lag3_file="${OUTPUT_DIR}/rq_factor_lag3_backtest_results.csv"
    lag5_file="${OUTPUT_DIR}/rq_factor_lag5_backtest_results.csv"
    
    all_complete=true
    
    if [ ! -f "$lag1_file" ]; then
        all_complete=false
        echo "[$(date +%H:%M:%S)] Waiting for lag 1 results..."
    fi
    
    if [ ! -f "$lag3_file" ]; then
        all_complete=false
        echo "[$(date +%H:%M:%S)] Waiting for lag 3 results..."
    fi
    
    if [ ! -f "$lag5_file" ]; then
        all_complete=false
        echo "[$(date +%H:%M:%S)] Waiting for lag 5 results..."
    fi
    
    # Check if process is still running
    if pgrep -f "backtest_rq_factor_lagged.py" > /dev/null; then
        if [ "$all_complete" = false ]; then
            echo "[$(date +%H:%M:%S)] Process still running, waiting..."
        fi
    else
        if [ "$all_complete" = false ]; then
            echo "[$(date +%H:%M:%S)] Process stopped but results incomplete. Checking log..."
            tail -50 "$LOG_FILE" | grep -E "(Backtest complete|Error|Exception)" | tail -5
        fi
    fi
    
    # If all complete, break
    if [ "$all_complete" = true ]; then
        echo ""
        echo "[$(date +%H:%M:%S)] All results complete! Generating plots..."
        break
    fi
    
    # Check timeout
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if [ $elapsed -gt $max_wait_seconds ]; then
        echo ""
        echo "[$(date +%H:%M:%S)] Timeout reached. Checking current status..."
        break
    fi
    
    sleep $CHECK_INTERVAL
done

echo ""
echo "=== Generating Comprehensive Plots ==="
cd /Users/dbe/etf-web
python lib/etf/functions/research/scripts/plot_rq_lagged_comparison.py

echo ""
echo "=== Plotting Complete ==="
echo "Check: data/research/sp500_backtest/rq_factor_lagged_comprehensive_comparison.png"

