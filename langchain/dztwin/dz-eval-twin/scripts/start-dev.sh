#!/bin/bash

# Development startup script for Gen AI Evaluation Platform

set -e

echo "=== Starting Gen AI Evaluation Platform (Development) ==="
echo ""

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null && ! docker ps | grep -q mongodb; then
    echo "Warning: MongoDB doesn't appear to be running"
    echo "Starting MongoDB with Docker..."
    docker run -d -p 27017:27017 --name mongodb mongo:latest || true
    sleep 3
fi

# Start backend in background
echo "Starting backend server..."
cd backend
source venv/bin/activate
python -m app.main &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Start frontend in background
echo "Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=== Development servers started ==="
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Access the application:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
