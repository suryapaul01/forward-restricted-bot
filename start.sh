#!/bin/bash

# Startup script for Restricted Content Download Bot
# This script ensures clean session handling and runs both web server and bot

echo "========================================"
echo "Starting Restricted Content Download Bot"
echo "Made by: Surya (@tataa_sumo)"
echo "========================================"

# Check if session file exists and is valid
if [ -f "idfinderpro.session" ]; then
    echo "Found existing session file..."
else
    echo "No session file found - will create new one..."
fi

# Create downloads directory if it doesn't exist
mkdir -p downloads

# Start Flask web server in background (required for Render/Railway health checks)
echo "Starting web server on port ${PORT:-8080}..."
gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 120 &

# Wait a moment for gunicorn to start
sleep 2

# Start the bot (this keeps running in foreground)
echo "Starting Telegram bot..."
python3 bot.py

