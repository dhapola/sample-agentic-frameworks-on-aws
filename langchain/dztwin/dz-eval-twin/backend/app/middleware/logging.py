"""Logging middleware for request/response tracking."""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and outgoing responses.
    
    Logs:
    - Request method, path, and customer context
    - Response status code
    - Request processing time
    - Any errors that occur during request processing
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        customer_id = getattr(request.state, "customer_id", None)
        
        # Log incoming request
        logger.info(
            f"Incoming request: {method} {path} "
            f"[customer_id={customer_id or 'none'}]"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {method} {path} "
                f"[status={response.status_code}] "
                f"[time={process_time:.3f}s] "
                f"[customer_id={customer_id or 'none'}]"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path} "
                f"[error={str(e)}] "
                f"[time={process_time:.3f}s] "
                f"[customer_id={customer_id or 'none'}]",
                exc_info=True
            )
            raise
