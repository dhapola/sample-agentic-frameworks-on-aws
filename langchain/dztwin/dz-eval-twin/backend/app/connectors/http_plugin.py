"""HTTP/REST plugin for connecting to gen AI applications via HTTP.

This module implements an HTTP/REST connector plugin that supports
configurable endpoints, authentication, timeouts, and retry logic.
"""

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from app.connectors.plugin import ApplicationResponse, BaseApplicationPlugin
from app.models.connection_config import ConnectionConfig


class HTTPPlugin(BaseApplicationPlugin):
    """
    HTTP/REST plugin for connecting to gen AI applications.
    
    Supports:
    - Configurable HTTP endpoints
    - Multiple authentication methods (Bearer, API Key, Basic)
    - Timeout configuration
    - Automatic retry logic with exponential backoff
    - Custom headers
    - Response parsing and error handling
    
    The plugin sends POST requests with JSON payloads containing
    the input text and expects JSON responses with an output field.
    """
    
    def __init__(self):
        """Initialize the HTTP plugin."""
        super().__init__("http")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self, config: ConnectionConfig) -> None:
        """
        Establish HTTP client with configuration.
        
        Creates an async HTTP client with the specified timeout,
        authentication, and custom headers.
        
        Args:
            config: Connection configuration including endpoint,
                   authentication, timeout, and retry settings
        
        Raises:
            ValueError: If configuration is invalid
            ConnectionError: If initial connection test fails
        """
        # Validate configuration
        await super().connect(config)
        
        # Build headers
        headers = self._build_headers(config)
        
        # Create HTTP client with timeout
        timeout = httpx.Timeout(
            timeout=float(config.timeout),
            connect=10.0,  # Connection timeout
            read=float(config.timeout),  # Read timeout
            write=10.0,  # Write timeout
            pool=5.0  # Pool timeout
        )
        
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True
        )
        
        # Test connection with a simple request (optional)
        # This helps catch configuration errors early
        try:
            # Verify the endpoint is reachable
            await self._test_connection()
        except Exception as e:
            # Clean up client if connection test fails
            await self._client.aclose()
            self._client = None
            self._connected = False
            raise ConnectionError(
                f"Failed to connect to {config.endpoint}: {str(e)}"
            ) from e
    
    async def disconnect(self) -> None:
        """
        Close HTTP client and clean up resources.
        
        Closes the async HTTP client and resets connection state.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
        
        await super().disconnect()
    
    async def send_input(self, input_text: str) -> ApplicationResponse:
        """
        Send input to the HTTP endpoint and receive response.
        
        Sends a POST request with the input text as JSON payload,
        measures latency, handles retries, and parses the response.
        
        Request format:
            POST {endpoint}
            Content-Type: application/json
            {
                "input": "<input_text>"
            }
        
        Expected response format:
            {
                "output": "<generated_text>",
                "metadata": { ... }  // optional
            }
        
        Args:
            input_text: The input text to send to the application
        
        Returns:
            ApplicationResponse containing output, latency, and metadata
        
        Raises:
            RuntimeError: If not connected
            ValueError: If input is invalid
            TimeoutError: If request exceeds configured timeout
        """
        self._validate_connected()
        self._validate_input(input_text)
        
        if not self._client:
            raise RuntimeError("HTTP client not initialized")
        
        # Prepare request payload
        payload = {"input": input_text}
        
        # Execute request with retry logic
        start_time = time.time()
        response_data = None
        error_message = None
        
        try:
            response_data = await self._send_with_retry(payload)
        except TimeoutError as e:
            error_message = f"Request timeout: {str(e)}"
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP {e.response.status_code}: {e.response.text}"
        except Exception as e:
            error_message = f"Request failed: {str(e)}"
        
        # Calculate latency
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Parse response
        if error_message:
            return ApplicationResponse(
                output="",
                latency=latency,
                error=error_message
            )
        
        return self._parse_response(response_data, latency)
    
    def is_connected(self) -> bool:
        """
        Check if the HTTP client is connected.
        
        Returns:
            True if connected and client is initialized, False otherwise
        """
        return self._connected and self._client is not None
    
    def _build_headers(self, config: ConnectionConfig) -> Dict[str, str]:
        """
        Build HTTP headers from configuration.
        
        Handles authentication and custom headers.
        
        Args:
            config: Connection configuration
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add authentication headers
        if config.authentication:
            auth_type = config.authentication.get("type", "").lower()
            
            if auth_type == "bearer":
                token = config.authentication.get("token")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            
            elif auth_type == "api_key":
                api_key = config.authentication.get("api_key")
                header_name = config.authentication.get("header_name", "X-API-Key")
                if api_key:
                    headers[header_name] = api_key
            
            elif auth_type == "basic":
                # Basic auth is handled by httpx.BasicAuth, not headers
                # We'll handle this in the request method
                pass
        
        # Add custom headers (these override defaults)
        if config.custom_headers:
            headers.update(config.custom_headers)
        
        return headers
    
    async def _test_connection(self) -> None:
        """
        Test the connection to the endpoint.
        
        Performs a simple HEAD or GET request to verify the endpoint
        is reachable. This is optional but helps catch errors early.
        
        Raises:
            Exception: If connection test fails
        """
        if not self._client or not self.config:
            return
        
        try:
            # Try HEAD request first (lightweight)
            response = await self._client.head(
                str(self.config.endpoint),
                timeout=5.0
            )
            # Accept any response (even 404) as long as we can connect
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot reach endpoint: {str(e)}") from e
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Connection timeout: {str(e)}") from e
    
    async def _send_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send HTTP request with retry logic.
        
        Implements exponential backoff retry strategy for transient failures.
        
        Args:
            payload: JSON payload to send
        
        Returns:
            Parsed JSON response
        
        Raises:
            TimeoutError: If request times out
            httpx.HTTPStatusError: If HTTP error occurs
            Exception: If all retries fail
        """
        if not self._client or not self.config:
            raise RuntimeError("Client not initialized")
        
        max_retries = self.config.retries
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Add basic auth if configured
                auth = None
                if self.config.authentication:
                    auth_type = self.config.authentication.get("type", "").lower()
                    if auth_type == "basic":
                        username = self.config.authentication.get("username")
                        password = self.config.authentication.get("password")
                        if username and password:
                            auth = httpx.BasicAuth(username, password)
                
                # Send POST request
                response = await self._client.post(
                    str(self.config.endpoint),
                    json=payload,
                    auth=auth
                )
                
                # Raise exception for HTTP errors (4xx, 5xx)
                response.raise_for_status()
                
                # Parse and return JSON response
                return response.json()
            
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(
                    f"Request timeout after {self.config.timeout}s"
                )
                # Don't retry on timeout
                raise last_exception from e
            
            except httpx.HTTPStatusError as e:
                # Retry on 5xx errors, not on 4xx (client errors)
                if e.response.status_code >= 500 and attempt < max_retries:
                    last_exception = e
                    # Exponential backoff: 1s, 2s, 4s, 8s...
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Don't retry on 4xx or if out of retries
                    raise
            
            except httpx.ConnectError as e:
                # Retry on connection errors
                if attempt < max_retries:
                    last_exception = e
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ConnectionError(
                        f"Failed to connect after {max_retries} retries: {str(e)}"
                    ) from e
            
            except Exception as e:
                # Unexpected error - don't retry
                raise RuntimeError(f"Unexpected error: {str(e)}") from e
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed after all retries")
    
    def _parse_response(
        self,
        response_data: Dict[str, Any],
        latency: float
    ) -> ApplicationResponse:
        """
        Parse HTTP response into ApplicationResponse.
        
        Extracts output, metadata, and error information from the
        JSON response.
        
        Args:
            response_data: Parsed JSON response
            latency: Measured latency in milliseconds
        
        Returns:
            ApplicationResponse with parsed data
        """
        # Extract output (required field)
        output = response_data.get("output", "")
        
        # Extract optional metadata
        metadata = response_data.get("metadata")
        
        # Extract optional error
        error = response_data.get("error")
        
        # If no output and no error, treat as error
        if not output and not error:
            error = "Response missing 'output' field"
        
        return ApplicationResponse(
            output=output,
            latency=latency,
            metadata=metadata,
            error=error
        )
