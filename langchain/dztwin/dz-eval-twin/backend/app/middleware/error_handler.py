"""Error handling middleware and exception handlers."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Error response structure."""
    
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    """API error response."""
    
    error: ErrorDetail


# Custom exception classes
class PlatformError(Exception):
    """Base exception for platform errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "PLATFORM_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationError(PlatformError):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(PlatformError):
    """Resource not found exception."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class DatabaseError(PlatformError):
    """Database operation error exception."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ConnectionError(PlatformError):
    """External connection error exception."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="CONNECTION_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class UnauthorizedError(PlatformError):
    """Unauthorized access exception."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(PlatformError):
    """Forbidden access exception."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


def create_error_response(
    code: str,
    message: str,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create standardized error response."""
    error_detail = ErrorDetail(
        code=code,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc),
    )
    return ErrorResponse(error=error_detail).model_dump(mode='json')


async def error_handler_middleware(request: Request, call_next):
    """
    Middleware to catch and handle all exceptions.
    
    Converts exceptions to standardized error responses.
    """
    try:
        return await call_next(request)
    except PlatformError as e:
        logger.error(
            f"Platform error: {e.message} [code={e.code}]",
            exc_info=True
        )
        error_response = create_error_response(
            code=e.code,
            message=e.message,
            details=e.details,
        )
        return JSONResponse(
            status_code=e.status_code,
            content=error_response,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error: {str(e)}",
            exc_info=True
        )
        error_response = create_error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details=str(e) if logger.level == logging.DEBUG else None,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response,
        )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Converts validation errors to standardized error responses.
    """
    logger.warning(f"Validation error: {exc.errors()}")
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        ),
    )
