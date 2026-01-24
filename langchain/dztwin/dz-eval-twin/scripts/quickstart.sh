#!/bin/bash
# Quick start script for Gen AI Evaluation Platform

set -e

echo "🚀 Gen AI Evaluation Platform - Quick Start"
echo "==========================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v finch &> /dev/null; then
    echo "❌ Finch is not installed. Please install from: https://runfinch.com/"
    exit 1
fi
echo "✅ Finch is installed"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✅ Python 3 is installed"

# Start MongoDB
echo ""
echo "🗄️  Starting MongoDB 8..."
finch compose up -d

# Wait for MongoDB to be ready
echo "⏳ Waiting for MongoDB to be ready..."
sleep 5

# Initialize MongoDB
echo ""
echo "🔧 Initializing MongoDB with indexes..."
./scripts/init-mongodb.sh

# Test connection
echo ""
echo "🧪 Testing database connection..."
python scripts/test-mongodb-connection.py

# Setup backend
echo ""
echo "🐍 Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Start the backend:"
echo "      cd backend"
echo "      source venv/bin/activate"
echo "      python -m app.main"
echo ""
echo "   2. In another terminal, start the frontend:"
echo "      cd frontend"
echo "      npm install"
echo "      npm run dev"
echo ""
echo "   3. Access the application:"
echo "      - API: http://localhost:8000"
echo "      - API Docs: http://localhost:8000/docs"
echo "      - Frontend: http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "   - MongoDB Setup: MONGODB_SETUP.md"
echo "   - Project README: README.md"
echo ""
