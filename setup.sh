#!/bin/bash

# ============================================================================
# CVE_Scan - One-Click Setup for Linux/Mac
# Just run: chmod +x setup.sh && ./setup.sh
# ============================================================================

set -e

echo "============================================================================"
echo ""
echo "  CVE_SCAN - Automatic Setup"
echo "  Version 1.0"
echo ""
echo "============================================================================"
echo ""

# Check Python
echo "[1/5] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.11+ is required but not installed!"
    echo ""
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-venv"
    echo "  Mac: brew install python3"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo "✓ $PYTHON_VERSION found"

# Check Nmap
echo "[2/5] Checking Nmap installation..."
if ! command -v nmap &> /dev/null; then
    echo "WARNING: Nmap not found in PATH"
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install nmap"
    echo "  Mac: brew install nmap"
fi
echo "✓ Nmap check completed"

# Create virtual environment
echo "[3/5] Creating Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate and install
echo "[4/5] Installing packages..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Packages installed successfully"

# Verify
echo "[5/5] Verifying installation..."
python verify_installation.py || true

# Success
clear
echo "============================================================================"
echo ""
echo "  ✓ CVE_SCAN SETUP COMPLETE!"
echo ""
echo "============================================================================"
echo ""
echo "  You can now start scanning!"
echo ""
echo "  To run the application:"
echo "    Option 1: python app.py"
echo "    Option 2: source venv/bin/activate && python app.py"
echo ""
echo "============================================================================"
echo ""
