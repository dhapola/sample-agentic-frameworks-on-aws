"""Unit tests for middleware components."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware import CustomerContextMiddleware, LoggingMiddleware
from app.middleware.error_handler import (
    PlatformError,
    ValidationError,
    NotFoundError,
    error_handler_middleware,
)


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    
    # Add middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CustomerContextMiddleware)
    app.middleware("http")(error_handler_middleware)
    
    # Add test routes
    @app.get("/api/test")
    async def test_route(request: Request):
        customer_id = getattr(request.state, "customer_id", None)
        return {"customer_id": customer_id}
    
    @app.get("/api/health")
    async def health_route():
        return {"status": "ok"}
    
    @app.get("/api/error")
    async def error_route():
        raise PlatformError("Test error", code="TEST_ERROR")
    
    @app.get("/api/not-found")
    async def not_found_route():
        raise NotFoundError("Resource not found")
    
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


def test_customer_context_middleware_with_header(client):
    """Test that customer context is extracted from header."""
    response = client.get(
        "/api/test",
        headers={"X-Customer-ID": "test-customer-123"}
    )
    assert response.status_code == 200
    assert response.json()["customer_id"] == "test-customer-123"


def test_customer_context_middleware_without_header(client):
    """Test that customer context is None when header is missing."""
    response = client.get("/api/test")
    assert response.status_code == 200
    assert response.json()["customer_id"] is None


def test_customer_context_middleware_exempt_path(client):
    """Test that exempt paths don't require customer context."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_logging_middleware_adds_process_time(client):
    """Test that logging middleware adds process time header."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    assert float(response.headers["X-Process-Time"]) >= 0


def test_error_handler_middleware_platform_error(client):
    """Test that error handler converts PlatformError to JSON response."""
    response = client.get("/api/error")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "TEST_ERROR"
    assert data["error"]["message"] == "Test error"
    assert "timestamp" in data["error"]


def test_error_handler_middleware_not_found(client):
    """Test that error handler converts NotFoundError to 404 response."""
    response = client.get("/api/not-found")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Resource not found"


def test_validation_error_creation():
    """Test ValidationError exception creation."""
    error = ValidationError("Invalid input", details={"field": "name"})
    assert error.message == "Invalid input"
    assert error.code == "VALIDATION_ERROR"
    assert error.status_code == 400
    assert error.details == {"field": "name"}


def test_not_found_error_creation():
    """Test NotFoundError exception creation."""
    error = NotFoundError("Dataset not found")
    assert error.message == "Dataset not found"
    assert error.code == "NOT_FOUND"
    assert error.status_code == 404
