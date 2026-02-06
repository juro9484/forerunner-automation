#!/bin/bash
set -e

echo "=========================================="
echo "Forerunner Claims Automation - VM Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "ERROR: Do not run this script as root or with sudo"
   echo "Run it as your regular user: ./setup.sh"
   exit 1
fi

# Update system
echo "[1/8] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11
echo "[2/8] Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install system dependencies for Playwright
echo "[3/8] Installing system dependencies..."
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    git

# Create Python virtual environment
echo "[4/8] Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "[5/8] Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "[6/8] Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "[7/8] Installing Playwright browsers (this may take a few minutes)..."
playwright install chromium
playwright install-deps chromium

# Create necessary directories
echo "[8/8] Creating directories..."
mkdir -p logs
mkdir -p screenshots
mkdir -p data/attachments
mkdir -p data/backups

# Set up .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "=========================================="
    echo "IMPORTANT: Configure your .env file"
    echo "=========================================="
    echo "Copy .env.example to .env and fill in your credentials:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
fi

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure your .env file with credentials"
echo "2. Install the systemd service: sudo ./install-service.sh"
echo "3. Start the service: sudo systemctl start forerunner-monitor"
echo ""
