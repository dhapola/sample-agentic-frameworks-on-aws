.PHONY: help setup install-backend install-frontend start-db stop-db start-backend start-frontend test test-backend test-frontend clean

help:
	@echo "Gen AI Evaluation Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              - Complete project setup"
	@echo "  make install-backend    - Install backend dependencies"
	@echo "  make install-frontend   - Install frontend dependencies"
	@echo ""
	@echo "Database:"
	@echo "  make start-db           - Start MongoDB with Docker Compose"
	@echo "  make stop-db            - Stop MongoDB"
	@echo ""
	@echo "Development:"
	@echo "  make start-backend      - Start backend development server"
	@echo "  make start-frontend     - Start frontend development server"
	@echo ""
	@echo "Testing:"
	@echo "  make test               - Run all tests"
	@echo "  make test-backend       - Run backend tests"
	@echo "  make test-frontend      - Run frontend tests"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              - Remove generated files and dependencies"

setup:
	@echo "Setting up Gen AI Evaluation Platform..."
	@./scripts/setup.sh

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

start-db:
	@echo "Starting MongoDB..."
	docker-compose up -d mongodb
	@echo "MongoDB started on port 27017"

stop-db:
	@echo "Stopping MongoDB..."
	docker-compose down

start-backend:
	@echo "Starting backend server..."
	cd backend && . venv/bin/activate && python -m app.main

start-frontend:
	@echo "Starting frontend server..."
	cd frontend && npm run dev

test:
	@echo "Running all tests..."
	@./scripts/run-tests.sh

test-backend:
	@echo "Running backend tests..."
	cd backend && . venv/bin/activate && pytest -v

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test -- --passWithNoTests

clean:
	@echo "Cleaning up..."
	rm -rf backend/venv
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf backend/htmlcov
	rm -rf backend/.coverage
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf frontend/coverage
	@echo "Cleanup complete"
