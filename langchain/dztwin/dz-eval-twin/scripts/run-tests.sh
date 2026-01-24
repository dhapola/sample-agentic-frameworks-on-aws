#!/bin/bash

# Test runner script for Gen AI Evaluation Platform

set -e

echo "=== Running Gen AI Evaluation Platform Tests ==="
echo ""

# Backend tests
echo "Running backend tests..."
cd backend
source venv/bin/activate
pytest -v
cd ..
echo "Backend tests complete!"
echo ""

# Frontend tests
echo "Running frontend tests..."
cd frontend
npm test -- --passWithNoTests
cd ..
echo "Frontend tests complete!"
echo ""

echo "=== All tests passed ==="
