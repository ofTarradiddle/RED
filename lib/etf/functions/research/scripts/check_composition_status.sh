#!/bin/bash
# Monitor portfolio composition reconstruction and notify when complete

cd /Users/dbe/etf-web

COMPOSITION_FILE="data/research/sp500_backtest/innovation_factor_portfolio_composition.csv"
LOG_FILE="/tmp/reconstruct_final.log"

echo "Monitoring portfolio composition reconstruction..."
echo "Checking every 30 seconds..."
echo ""

while [ ! -f "$COMPOSITION_FILE" ]; do
    sleep 30
    if ps aux | grep -q "[r]econstruct_portfolio_composition"; then
        PROGRESS=$(tail -5 "$LOG_FILE" 2>/dev/null | grep -o "Processing [0-9]*/[0-9]*" | tail -1 || echo "Processing...")
        echo "[$(date +%H:%M:%S)] Still running... $PROGRESS"
    else
        echo "[$(date +%H:%M:%S)] Process not found, but file doesn't exist yet"
        sleep 5
    fi
done

echo ""
echo "=========================================="
echo "✓✓✓ PORTFOLIO COMPOSITION COMPLETE! ✓✓✓"
echo "=========================================="
echo ""
echo "File: $COMPOSITION_FILE"
ls -lh "$COMPOSITION_FILE"
echo ""
echo "Total months: $(wc -l < "$COMPOSITION_FILE" | tr -d ' ') (including header)"
echo ""
echo "=== FIRST 5 MONTHS ==="
head -6 "$COMPOSITION_FILE" | cut -d',' -f1,2
echo ""
echo "=== LAST 5 MONTHS ==="
tail -6 "$COMPOSITION_FILE" | cut -d',' -f1,2
echo ""
echo "=== SAMPLE MONTH (showing tickers) ==="
head -3 "$COMPOSITION_FILE" | tail -1 | cut -d',' -f1,2,3
echo ""

