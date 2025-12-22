#!/bin/bash
# Automated setup script for Vast.ai deployment
# Run this script after connecting to your Vast.ai instance

set -e  # Exit on error

echo "🚀 Setting up API Key Finder on Vast.ai..."

# Update system
echo "📦 Updating system packages..."
apt-get update -qq

# Install required system packages
echo "📦 Installing Python 3.12, Git, and dependencies..."
apt-get install -y -qq python3.12 python3.12-venv python3-pip git screen htop

# Verify installations
echo "✅ Verifying installations..."
python3.12 --version
git --version

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip -q

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt -q

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p downloaded_repos

# Check if repo_list.txt exists and has content
if [ ! -f "repo_list.txt" ] || [ ! -s "repo_list.txt" ]; then
    echo "⚠️  repo_list.txt is empty or missing. Generating repository list..."
    python3.12 big.py
fi

# Set permissions
chmod +x run_terminal.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Run in terminal mode: python3.12 run_terminal.py"
echo "   2. Run with web interface: python3.12 app.py"
echo "   3. Use screen to keep running: screen -S api-finder"
echo ""
echo "💡 Tip: Use 'screen -r api-finder' to reattach to your session"

