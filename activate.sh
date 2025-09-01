#!/bin/bash

# Development environment activation script
# Usage: source activate.sh

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Run: python3 -m venv venv"
    return 1
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded from .env"
else
    echo "⚠️  .env file not found. Copy .env.example to .env and configure"
fi

echo ""
echo "🏥 Doctor Watch Development Environment Ready!"
echo ""
echo "Available commands:"
echo "  python test_monitor.py    # Test the monitoring system"
echo "  cd doctor-watch && func start    # Run Azure Function locally"
echo "  ./deploy.sh              # Deploy to Azure"
