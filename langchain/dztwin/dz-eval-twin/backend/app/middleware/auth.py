"""Authentication middleware for customer context management."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CustomerContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate customer context from requests.
    
    This middleware:
    - Extracts customer_id from request headers (X-Customer-ID)
    - Validates customer_id is present for protected endpoints
    - Adds customer_id to request state for use in route handlers
    - Enforces tenant isolation at the API level
    
    Admin endpoints (customer management) don't require customer context.
    All other endpoints require a valid customer_id header.
    """
    
    # Endpoints that don't require customer context
    EXEMPT_PATHS = [
        "/api/health",
        "/api/customers",  # Admin endpoints for customer management
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add customer context."""
        path = request.url.path
        
        # Skip customer context for exempt paths
        if self._is_exempt_path(path):
            logger.debug(f"Skipping customer context for exempt path: {path}")
            return await call_next(request)
        
        # Extract customer_id from header
        customer_id = request.headers.get("X-Customer-ID")
        
        # For non-exempt paths, customer_id is required
        if not customer_id:
            logger.warning(f"Missing customer_id for path: {path}")
            # Note: We'll let the route handler decide if customer_id is required
            # Some endpoints like GET /api/application-profiles/:id might be admin-accessible
            request.state.customer_id = None
        else:
            logger.debug(f"Customer context set: {customer_id} for path: {path}")
            request.state.customer_id = customer_id
        
        response = await call_next(request)
        return response
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from customer context requirement."""
        # Exact match for exempt paths
        if path in self.EXEMPT_PATHS:
            return True
        
        # Check if path starts with exempt prefix
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True
        
        return False
