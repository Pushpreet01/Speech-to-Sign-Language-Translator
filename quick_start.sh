#!/bin/bash

echo "🤟 Speech-to-Sign MVP Quick Start"
echo "====================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+ first."
    exit 1
fi

echo "✅ Python found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "🚀 Setup complete! Choose an option:"
echo ""
echo "1. Local Demo (no AWS required) - recommended for quick testing"
echo "2. Full AWS Setup (requires AWS credentials)"
echo ""
read -p "Enter your choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "🎭 Starting LOCAL DEMO mode..."
    echo "This mode uses mock data and doesn't require AWS setup"
    echo "Open your browser to: http://localhost:5000"
    echo ""
    python3 local_demo.py
elif [ "$choice" = "2" ]; then
    echo ""
    echo "☁️ Starting AWS mode..."
    echo "Make sure you have configured your .env file first!"
    echo ""
    python3 app.py
else
    echo "Invalid choice. Starting local demo by default..."
    python3 local_demo.py
fi
