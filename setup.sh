#!/bin/bash
# Quick start script for Server Profiler

set -e

echo "Server Profiler - Quick Start"
echo "=============================="
echo ""

# Check Python version
echo "→ Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "→ Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "→ Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "→ Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Make profiler executable
chmod +x profiler.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run the profiler:"
echo "     python profiler.py --help"
echo ""
echo "  3. Example usage:"
echo "     python profiler.py --host YOUR_SERVER --user admin --key ~/.ssh/key.pem"
echo ""
echo "  4. Or use the Makefile:"
echo "     make profile HOST=YOUR_SERVER KEY=~/.ssh/key.pem"
echo ""
