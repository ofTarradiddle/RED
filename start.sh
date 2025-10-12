#!/bin/bash

echo "🚀 Starting RED ETF Website Server..."
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Make the serve.py script executable
chmod +x serve.py

# Start the server
python3 serve.py
