#!/bin/bash

# Setup script for Gen AI Evaluation Platform

set -e

echo "=== Gen AI Evaluation Platform Setup ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

if ! command -v mongod &> /dev/null; then
    echo "Warning: MongoDB is not installed or not in PATH"
    echo "You can install it or run it via Docker"
fi

echo "Prerequisites check passed!"
echo ""

# Setup backend
echo "Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

cd ..
echo "Backend setup complete!"
echo ""

# Setup frontend
echo "Setting up frontend..."
cd frontend

echo "Installing Node dependencies..."
npm install

if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

cd ..
echo "Frontend setup complete!"
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Start MongoDB (if not running):"
echo "   docker run -d -p 27017:27017 --name mongodb mongo:latest"
echo ""
echo "2. Start the backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m app.main"
echo ""
echo "3. Start the frontend (in a new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
