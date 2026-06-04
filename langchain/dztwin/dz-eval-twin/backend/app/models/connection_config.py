"""Connection configuration model for gen AI applications."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ConnectionConfig(BaseModel):
    """
    Configuration for connecting to a gen AI application.
    
    Defines how the platform connects to and communicates with
    a generative AI application for evaluation.
    """
    
    endpoint: str = Field(..., description="Application endpoint URL (supports http, https, ws, wss schemes)")
    authentication: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Authentication configuration (API keys, tokens, etc.)"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retry attempts on failure"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom HTTP headers to include in requests"
    )
    
    @field_validator('endpoint')
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate endpoint is a valid URL."""
        if not v or not v.strip():
            raise ValueError("Endpoint cannot be empty")
        v = v.strip()
        # Basic URL validation
        if not (v.startswith('http://') or v.startswith('https://') or 
                v.startswith('ws://') or v.startswith('wss://')):
            raise ValueError("Endpoint must start with http://, https://, ws://, or wss://")
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is reasonable."""
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        if v > 300:
            raise ValueError("Timeout cannot exceed 300 seconds (5 minutes)")
        return v
    
    @field_validator('retries')
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Validate retry count is reasonable."""
        if v < 0:
            raise ValueError("Retries cannot be negative")
        if v > 10:
            raise ValueError("Retries cannot exceed 10")
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "endpoint": "https://api.example.com/v1/chat",
                "authentication": {
                    "type": "bearer",
                    "token": "sk-..."
                },
                "timeout": 30,
                "retries": 3,
                "custom_headers": {
                    "X-Custom-Header": "value"
                }
            }
        }
