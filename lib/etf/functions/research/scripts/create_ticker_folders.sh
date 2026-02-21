#!/bin/bash
# Script to create ticker folders on external drive
# Run this manually to set up the directory structure

BASE_PATH="/Volumes/My Passport/REDI"
SYMBOLS=("NVDA" "GLW" "ANET")
STATEMENT_TYPES=("income" "balance" "cashflow")

echo "Creating ticker folders on external drive..."
echo "Base path: $BASE_PATH"
echo ""

for symbol in "${SYMBOLS[@]}"; do
    for stmt in "${STATEMENT_TYPES[@]}"; do
        DIR="$BASE_PATH/$symbol/$stmt"
        echo "Creating: $DIR"
        mkdir -p "$DIR"
        
        if [ -d "$DIR" ]; then
            echo "  ✓ Created successfully"
        else
            echo "  ✗ Failed to create"
        fi
    done
done

echo ""
echo "Done! Folders created:"
for symbol in "${SYMBOLS[@]}"; do
    echo "  $BASE_PATH/$symbol/"
done

