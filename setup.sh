#!/bin/bash

# UPI Secure Pay AI - Backend Setup Script

echo "=========================================="
echo "  UPI Secure Pay AI - Backend Setup"
echo "=========================================="

# Check Python version
echo ""
echo "[1/7] Checking Python version..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python not found. Please install Python 3.10+"
    exit 1
fi
echo "✅ Python is installed"

# Create virtual environment
echo ""
echo "[2/7] Creating virtual environment..."
python -m venv venv
if [ $? -eq 0 ]; then
    echo "✅ Virtual environment created"
else
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo ""
echo "[3/7] Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"

# Install dependencies
echo ""
echo "[4/7] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Copy environment file
echo ""
echo "[5/7] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Environment file created"
else
    echo "✅ Environment file already exists"
fi

# Create models directory
echo ""
echo "[6/7] Creating directories..."
mkdir -p models/lightgbm models/transformer models/gnn models/tgn models/llm
echo "✅ Directories created"

echo ""
echo "[7/7] Setup complete!"
echo ""
echo "=========================================="
echo "  Next Steps:"
echo "=========================================="
echo ""
echo "1. Start PostgreSQL, Redis, Kafka (via Docker)"
echo "2. Run the server:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/api/v1/health"
echo ""
echo "=========================================="
