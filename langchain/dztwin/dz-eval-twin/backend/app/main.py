"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.connection import database_manager
from app.middleware import (
    CustomerContextMiddleware,
    LoggingMiddleware,
    error_handler_middleware,
)
from app.middleware.error_handler import validation_exception_handler
from app.api import customers, application_profiles, datasets, evaluations

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Gen AI Evaluation Platform API")
    try:
        await database_manager.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Gen AI Evaluation Platform API")
    await database_manager.disconnect()
    logger.info("Database connection closed")


# Create FastAPI application
app = FastAPI(
    title="Gen AI Evaluation Platform API",
    description="REST API for evaluating generative AI applications",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS (must be added first to handle preflight requests)
cors_origins = settings.cors_origins_list
allow_credentials = "*" not in cors_origins  # Credentials not allowed with wildcard

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add customer context middleware for tenant isolation
app.add_middleware(CustomerContextMiddleware)

# Add error handling middleware
app.middleware("http")(error_handler_middleware)

# Add validation exception handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Register API routers
app.include_router(customers.router)
app.include_router(application_profiles.router)
app.include_router(datasets.router)
app.include_router(evaluations.router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    db_status = "connected" if database_manager.is_connected() else "disconnected"
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
