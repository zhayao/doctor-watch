#!/bin/bash

# Quick setup script for Doctor Watch
# Run this script to set up the development environment

set -e

echo "🏥 Doctor Watch - Development Setup"
echo "==================================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r doctor-watch/requirements.txt
pip install -r requirements-dev.txt

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your actual credentials!"
else
    echo "📝 .env file already exists"
fi

# Check for Azure Functions Core Tools
if command -v func &> /dev/null; then
    echo "✅ Azure Functions Core Tools found"
else
    echo "⚠️  Azure Functions Core Tools not found"
    echo "   Install with: npm install -g azure-functions-core-tools@4 --unsafe-perm true"
fi

echo ""
echo "✅ Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Pushover credentials"
echo "2. Run: source activate.sh"
echo "3. Test: python test_monitor.py"
echo "4. Deploy: ./deploy.sh"
