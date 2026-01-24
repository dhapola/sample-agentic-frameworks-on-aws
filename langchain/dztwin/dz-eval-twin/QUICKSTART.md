# Quick Start Guide

Get the Gen AI Evaluation Platform up and running in minutes!

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Docker (for MongoDB) or MongoDB Community Edition installed locally

## Quick Setup (Automated)

Run the automated setup script:

```bash
./scripts/setup.sh
```

This will:
- Create Python virtual environment
- Install backend dependencies
- Install frontend dependencies
- Create environment configuration files

## Start the Platform

### Option 1: Using Make (Recommended)

```bash
# Start MongoDB
make start-db

# In one terminal - start backend
make start-backend

# In another terminal - start frontend
make start-frontend
```

### Option 2: Manual Start

```bash
# Start MongoDB
docker-compose up -d

# Start backend (in one terminal)
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m app.main

# Start frontend (in another terminal)
cd frontend
npm run dev
```

## Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **MongoDB**: localhost:27017

## Verify Installation

Check the health endpoint:

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

## Run Tests

```bash
# Run all tests
make test

# Or run individually
make test-backend
make test-frontend
```

## Development Workflow

1. **Backend changes**: The FastAPI server auto-reloads on file changes
2. **Frontend changes**: Vite provides hot module replacement (HMR)
3. **Database changes**: MongoDB data persists in Docker volume

## Common Commands

```bash
# View all available commands
make help

# Stop MongoDB
make stop-db

# Clean up all generated files
make clean
```

## Project Structure Overview

```
├── backend/           # Python FastAPI backend
│   ├── app/          # Application code
│   └── tests/        # Backend tests
├── frontend/         # React TypeScript frontend
│   ├── src/          # Application code
│   └── tests/        # Frontend tests
└── scripts/          # Development scripts
```

## Next Steps

Now that the project structure is set up, the next tasks will implement:

1. **Task 2**: Data models and database layer with multi-tenant isolation
2. **Task 3**: Customer and application profile management
3. **Task 4**: Application connector plugins
4. **Task 5**: Evaluation engine
5. **Task 6**: REST API endpoints
6. **Task 7**: Web UI components

## Troubleshooting

### MongoDB Connection Issues

If you see database connection errors:

```bash
# Check if MongoDB is running
docker ps | grep mongodb

# View MongoDB logs
docker logs gen-ai-eval-mongodb

# Restart MongoDB
docker-compose restart mongodb
```

### Port Already in Use

If ports 3000 or 8000 are already in use:

**Backend**: Edit `backend/.env` and change `API_PORT`
**Frontend**: Edit `frontend/vite.config.ts` and change the `server.port`

### Python Virtual Environment Issues

```bash
# Recreate virtual environment
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node Modules Issues

```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## Getting Help

- Check the main [README.md](README.md) for detailed documentation
- Review backend documentation in [backend/README.md](backend/README.md)
- Review frontend documentation in [frontend/README.md](frontend/README.md)
- Check the spec files in `.kiro/specs/gen-ai-eval-platform/`

## Development Tips

1. **Use the API docs**: Visit http://localhost:8000/docs to explore and test API endpoints
2. **Check logs**: Both servers output detailed logs for debugging
3. **Hot reload**: Both frontend and backend support hot reloading during development
4. **Database inspection**: Use MongoDB Compass or mongosh to inspect the database

Happy coding! 🚀
