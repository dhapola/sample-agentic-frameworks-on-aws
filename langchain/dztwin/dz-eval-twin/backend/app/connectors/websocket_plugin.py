"""WebSocket plugin for connecting to gen AI applications via WebSocket.

This module implements a WebSocket connector plugin that supports
real-time streaming applications with connection lifecycle management
and message framing.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import (
    ConnectionClosed,
    InvalidURI,
    WebSocketException,
)

from app.connectors.plugin import ApplicationResponse, BaseApplicationPlugin
from app.models.connection_config import ConnectionConfig


class WebSocketPlugin(BaseApplicationPlugin):
    """
    WebSocket plugin for connecting to gen AI applications.
    
    Supports:
    - WebSocket connection lifecycle management
    - Message framing and serialization
    - Configurable timeouts
    - Automatic reconnection on connection loss
    - JSON message format
    - Authentication via connection headers or initial handshake
    - Error handling for connection and message failures
    
    The plugin sends JSON messages with the input text and expects
    JSON responses with an output field.
    
    Message format (sent):
        {
            "type": "input",
            "input": "<input_text>"
        }
    
    Expected response format:
        {
            "type": "output",
            "output": "<generated_text>",
            "metadata": { ... }  // optional
        }
    """
    
    def __init__(self):
        """Initialize the WebSocket plugin."""
        super().__init__("websocket")
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._connection_lock = asyncio.Lock()
    
    async def connect(self, config: ConnectionConfig) -> None:
        """
        Establish WebSocket connection with configuration.
        
        Creates a WebSocket connection to the specified endpoint with
        authentication headers and timeout settings.
        
        Args:
            config: Connection configuration including endpoint,
                   authentication, timeout, and retry settings
        
        Raises:
            ValueError: If configuration is invalid
            ConnectionError: If connection cannot be established
        """
        # Validate configuration
        await super().connect(config)
        
        # Validate WebSocket URI
        if not self._is_valid_websocket_uri(str(config.endpoint)):
            raise ValueError(
                f"Invalid WebSocket URI: {config.endpoint}. "
                "Must start with ws:// or wss://"
            )
        
        # Build connection headers
        headers = self._build_headers(config)
        
        # Attempt connection with retries
        last_exception = None
        max_retries = config.retries
        
        for attempt in range(max_retries + 1):
            try:
                async with self._connection_lock:
                    # Connect to WebSocket endpoint
                    self._websocket = await asyncio.wait_for(
                        websockets.connect(
                            str(config.endpoint),
                            extra_headers=headers,
                            ping_interval=20,  # Send ping every 20s
                            ping_timeout=10,   # Wait 10s for pong
                            close_timeout=10,  # Wait 10s for close handshake
                        ),
                        timeout=float(config.timeout)
                    )
                    
                    # Connection successful
                    self._connected = True
                    return
            
            except asyncio.TimeoutError as e:
                last_exception = TimeoutError(
                    f"WebSocket connection timeout after {config.timeout}s"
                )
                if attempt >= max_retries:
                    self._connected = False
                    raise ConnectionError(str(last_exception)) from e
            
            except InvalidURI as e:
                # Don't retry on invalid URI
                self._connected = False
                raise ValueError(f"Invalid WebSocket URI: {str(e)}") from e
            
            except WebSocketException as e:
                last_exception = e
                if attempt >= max_retries:
                    self._connected = False
                    raise ConnectionError(
                        f"Failed to connect to WebSocket after {max_retries} retries: {str(e)}"
                    ) from e
            
            except Exception as e:
                # Unexpected error - don't retry
                self._connected = False
                raise ConnectionError(f"WebSocket connection failed: {str(e)}") from e
            
            # Wait before retry with exponential backoff
            if attempt < max_retries:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        # If we get here, all retries failed
        self._connected = False
        if last_exception:
            raise ConnectionError(str(last_exception)) from last_exception
    
    async def disconnect(self) -> None:
        """
        Close WebSocket connection and clean up resources.
        
        Closes the WebSocket connection gracefully and resets connection state.
        """
        async with self._connection_lock:
            if self._websocket:
                try:
                    await self._websocket.close()
                except Exception:
                    # Ignore errors during close
                    pass
                finally:
                    self._websocket = None
        
        await super().disconnect()
    
    async def send_input(self, input_text: str) -> ApplicationResponse:
        """
        Send input to the WebSocket endpoint and receive response.
        
        Sends a JSON message with the input text, measures latency,
        and parses the response.
        
        Message format:
            {
                "type": "input",
                "input": "<input_text>"
            }
        
        Expected response format:
            {
                "type": "output",
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
        
        if not self._websocket:
            raise RuntimeError("WebSocket not initialized")
        
        # Prepare message
        message = {
            "type": "input",
            "input": input_text
        }
        
        # Send message and receive response
        start_time = time.time()
        response_data = None
        error_message = None
        
        try:
            response_data = await self._send_and_receive(message)
        except TimeoutError as e:
            error_message = f"Request timeout: {str(e)}"
        except ConnectionClosed as e:
            error_message = f"WebSocket connection closed: {str(e)}"
            # Mark as disconnected
            self._connected = False
        except WebSocketException as e:
            error_message = f"WebSocket error: {str(e)}"
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
        Check if the WebSocket is connected.
        
        Returns:
            True if connected and WebSocket is open, False otherwise
        """
        return (
            self._connected
            and self._websocket is not None
            and self._websocket.open
        )
    
    def _is_valid_websocket_uri(self, uri: str) -> bool:
        """
        Validate WebSocket URI format.
        
        Args:
            uri: The URI to validate
        
        Returns:
            True if valid WebSocket URI, False otherwise
        """
        return uri.startswith("ws://") or uri.startswith("wss://")
    
    def _build_headers(self, config: ConnectionConfig) -> Dict[str, str]:
        """
        Build WebSocket connection headers from configuration.
        
        Handles authentication and custom headers.
        
        Args:
            config: Connection configuration
        
        Returns:
            Dictionary of WebSocket headers
        """
        headers = {}
        
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
            
            # Note: Basic auth for WebSocket is typically handled via URL
            # or custom headers, not standard Basic auth header
        
        # Add custom headers (these override defaults)
        if config.custom_headers:
            headers.update(config.custom_headers)
        
        return headers
    
    async def _send_and_receive(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send message and receive response via WebSocket.
        
        Args:
            message: Message dictionary to send
        
        Returns:
            Parsed JSON response
        
        Raises:
            TimeoutError: If request times out
            ConnectionClosed: If connection is closed
            WebSocketException: If WebSocket error occurs
            ValueError: If response is not valid JSON
        """
        if not self._websocket or not self.config:
            raise RuntimeError("WebSocket not initialized")
        
        # Serialize message to JSON
        message_json = json.dumps(message)
        
        # Send message
        await asyncio.wait_for(
            self._websocket.send(message_json),
            timeout=float(self.config.timeout)
        )
        
        # Receive response
        response_text = await asyncio.wait_for(
            self._websocket.recv(),
            timeout=float(self.config.timeout)
        )
        
        # Parse JSON response
        try:
            response_data = json.loads(response_text)
            return response_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}") from e
    
    def _parse_response(
        self,
        response_data: Dict[str, Any],
        latency: float
    ) -> ApplicationResponse:
        """
        Parse WebSocket response into ApplicationResponse.
        
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
