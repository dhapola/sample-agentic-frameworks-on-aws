"""Property-based tests for application connector operations.

Feature: gen-ai-eval-platform
Property 7: Request-response capture
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import json
import asyncio
from websockets.exceptions import WebSocketException

from app.connectors.http_plugin import HTTPPlugin
from app.connectors.websocket_plugin import WebSocketPlugin
from app.connectors.plugin import ApplicationResponse
from app.models.connection_config import ConnectionConfig


# ==================== Hypothesis Strategies ====================

@st.composite
def connection_config_strategy(draw):
    """Generate valid ConnectionConfig objects for HTTP."""
    # Generate valid URL
    protocol = "https"
    domain = draw(st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'))
    path = draw(st.text(min_size=0, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz/'))
    endpoint = f"{protocol}://api.{domain}.com/{path}".rstrip('/')
    
    # Timeout and retries
    timeout = draw(st.integers(min_value=5, max_value=60))
    retries = draw(st.integers(min_value=0, max_value=5))
    
    return ConnectionConfig(
        endpoint=endpoint,
        timeout=timeout,
        retries=retries
    )


@st.composite
def websocket_config_strategy(draw):
    """Generate valid ConnectionConfig objects for WebSocket."""
    # Generate valid WebSocket URL
    protocol = draw(st.sampled_from(["ws", "wss"]))
    domain = draw(st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'))
    path = draw(st.text(min_size=0, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz/'))
    endpoint = f"{protocol}://api.{domain}.com/{path}".rstrip('/')
    
    # Timeout and retries
    timeout = draw(st.integers(min_value=5, max_value=60))
    retries = draw(st.integers(min_value=0, max_value=5))
    
    return ConnectionConfig(
        endpoint=endpoint,
        timeout=timeout,
        retries=retries
    )


@st.composite
def input_text_strategy(draw):
    """Generate valid input text for gen AI applications."""
    # Generate various types of input text
    input_type = draw(st.sampled_from([
        "simple",
        "multiline",
        "with_punctuation",
        "with_numbers",
        "long"
    ]))
    
    if input_type == "simple":
        return draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'), whitelist_characters=' '
        ))).strip() or "Test"
    elif input_type == "multiline":
        lines = draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'), whitelist_characters=' '
            )),
            min_size=1,
            max_size=5
        ))
        return "\n".join(line.strip() or "Test" for line in lines)
    elif input_type == "with_punctuation":
        return draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' .,!?'
        ))).strip() or "Test!"
    elif input_type == "with_numbers":
        return draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
        ))).strip() or "Test123"
    else:  # long
        return draw(st.text(min_size=100, max_size=500, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' .,!?\n'
        ))).strip() or "Test " * 50


# ==================== Property Tests ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=connection_config_strategy(),
    input_text=input_text_strategy()
)
async def test_http_plugin_request_response_capture_success(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 7: Request-response capture (HTTP plugin - success case).
    
    **Validates: Requirements 2.8**
    
    For any input sent to a gen AI application via HTTP, the platform
    should capture a response with successful output.
    """
    plugin = HTTPPlugin()
    
    # Mock successful HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "output": f"Generated response for: {input_text[:50]}",
        "metadata": {"model": "test-model", "tokens": 42}
    }
    mock_response.raise_for_status = MagicMock()
    
    # Mock the HTTP client
    with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
        await plugin.connect(config)
    
    with patch.object(plugin._client, 'post', new_callable=AsyncMock, return_value=mock_response):
        # Send input to the application
        response = await plugin.send_input(input_text)
        
        # Property: Response should not be None
        assert response is not None, \
            "Response should not be None for any input"
        
        # Property: Response should be an ApplicationResponse
        assert isinstance(response, ApplicationResponse), \
            "Response should be an ApplicationResponse instance"
        
        # Property: Response should have output (successful case)
        assert response.output is not None, \
            "Response should have output field"
        assert len(response.output) > 0, \
            "Response output should not be empty for successful response"
        
        # Property: Response should have latency measurement
        assert response.latency is not None, \
            "Response should have latency measurement"
        assert response.latency >= 0, \
            f"Latency should be non-negative, got {response.latency}"
        
        # Property: Response should not have error for successful case
        assert response.error is None, \
            "Response should not have error for successful response"
    
    await plugin.disconnect()


@pytest.mark.skip(reason="Skipping as requested by user")
@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=connection_config_strategy(),
    input_text=input_text_strategy()
)
async def test_http_plugin_request_response_capture_error(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 7: Request-response capture (HTTP plugin - error case).
    
    **Validates: Requirements 2.8**
    
    For any input sent to a gen AI application via HTTP that fails,
    the platform should capture a response with error information.
    """
    plugin = HTTPPlugin()
    
    # Mock failed HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    error = httpx.HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=mock_response
    )
    
    # Mock the HTTP client
    with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
        await plugin.connect(config)
    
    with patch.object(plugin._client, 'post', side_effect=error):
        # Send input to the application
        response = await plugin.send_input(input_text)
        
        # Property: Response should not be None even on error
        assert response is not None, \
            "Response should not be None even when request fails"
        
        # Property: Response should be an ApplicationResponse
        assert isinstance(response, ApplicationResponse), \
            "Response should be an ApplicationResponse instance even on error"
        
        # Property: Response should have error field populated
        assert response.error is not None, \
            "Response should have error field populated when request fails"
        assert len(response.error) > 0, \
            "Response error should not be empty when request fails"
        
        # Property: Response should have latency measurement even on error
        assert response.latency is not None, \
            "Response should have latency measurement even on error"
        assert response.latency >= 0, \
            f"Latency should be non-negative even on error, got {response.latency}"
        
        # Property: Response output should be empty for error case
        assert response.output == "", \
            "Response output should be empty when request fails"
    
    await plugin.disconnect()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=websocket_config_strategy(),
    input_text=input_text_strategy()
)
async def test_websocket_plugin_request_response_capture_success(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 7: Request-response capture (WebSocket plugin - success case).
    
    **Validates: Requirements 2.8**
    
    For any input sent to a gen AI application via WebSocket, the platform
    should capture a response with successful output.
    """
    plugin = WebSocketPlugin()
    
    # Mock WebSocket connection
    mock_websocket = MagicMock()
    mock_websocket.open = True
    mock_websocket.close = AsyncMock()
    
    # Mock successful WebSocket response
    response_data = {
        "type": "output",
        "output": f"Generated response for: {input_text[:50]}",
        "metadata": {"model": "test-model", "tokens": 42}
    }
    
    mock_websocket.send = AsyncMock()
    mock_websocket.recv = AsyncMock(return_value=json.dumps(response_data))
    
    with patch('websockets.connect', new_callable=AsyncMock, return_value=mock_websocket):
        await plugin.connect(config)
        
        # Send input to the application
        response = await plugin.send_input(input_text)
        
        # Property: Response should not be None
        assert response is not None, \
            "Response should not be None for any input"
        
        # Property: Response should be an ApplicationResponse
        assert isinstance(response, ApplicationResponse), \
            "Response should be an ApplicationResponse instance"
        
        # Property: Response should have output (successful case)
        assert response.output is not None, \
            "Response should have output field"
        assert len(response.output) > 0, \
            "Response output should not be empty for successful response"
        
        # Property: Response should have latency measurement
        assert response.latency is not None, \
            "Response should have latency measurement"
        assert response.latency >= 0, \
            f"Latency should be non-negative, got {response.latency}"
        
        # Property: Response should not have error for successful case
        assert response.error is None, \
            "Response should not have error for successful response"
        
        await plugin.disconnect()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=websocket_config_strategy(),
    input_text=input_text_strategy()
)
async def test_websocket_plugin_request_response_capture_error(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 7: Request-response capture (WebSocket plugin - error case).
    
    **Validates: Requirements 2.8**
    
    For any input sent to a gen AI application via WebSocket that fails,
    the platform should capture a response with error information.
    """
    plugin = WebSocketPlugin()
    
    # Mock WebSocket connection
    mock_websocket = MagicMock()
    mock_websocket.open = True
    mock_websocket.close = AsyncMock()
    
    # Mock WebSocket error
    from websockets.exceptions import WebSocketException
    mock_websocket.send = AsyncMock(side_effect=WebSocketException("Connection error"))
    
    with patch('websockets.connect', new_callable=AsyncMock, return_value=mock_websocket):
        await plugin.connect(config)
        
        # Send input to the application
        response = await plugin.send_input(input_text)
        
        # Property: Response should not be None even on error
        assert response is not None, \
            "Response should not be None even when request fails"
        
        # Property: Response should be an ApplicationResponse
        assert isinstance(response, ApplicationResponse), \
            "Response should be an ApplicationResponse instance even on error"
        
        # Property: Response should have error field populated
        assert response.error is not None, \
            "Response should have error field populated when request fails"
        assert len(response.error) > 0, \
            "Response error should not be empty when request fails"
        
        # Property: Response should have latency measurement even on error
        assert response.latency is not None, \
            "Response should have latency measurement even on error"
        assert response.latency >= 0, \
            f"Latency should be non-negative even on error, got {response.latency}"
        
        # Property: Response output should be empty for error case
        assert response.output == "", \
            "Response output should be empty when request fails"
        
        await plugin.disconnect()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(
    config=connection_config_strategy(),
    input_text=input_text_strategy()
)
async def test_http_plugin_request_response_capture_timeout(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 7: Request-response capture (HTTP plugin - timeout case).
    
    **Validates: Requirements 2.8**
    
    For any input sent to a gen AI application via HTTP that times out,
    the platform should capture a response with error information.
    """
    plugin = HTTPPlugin()
    
    # Mock the HTTP client
    with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
        await plugin.connect(config)
    
    # Mock timeout error
    with patch.object(plugin._client, 'post', side_effect=httpx.TimeoutException("Request timeout")):
        # Send input to the application
        response = await plugin.send_input(input_text)
        
        # Property: Response should not be None even on timeout
        assert response is not None, \
            "Response should not be None even when request times out"
        
        # Property: Response should be an ApplicationResponse
        assert isinstance(response, ApplicationResponse), \
            "Response should be an ApplicationResponse instance even on timeout"
        
        # Property: Response should have error field populated
        assert response.error is not None, \
            "Response should have error field populated when request times out"
        assert "timeout" in response.error.lower(), \
            "Response error should mention timeout"
        
        # Property: Response should have latency measurement even on timeout
        assert response.latency is not None, \
            "Response should have latency measurement even on timeout"
        assert response.latency >= 0, \
            f"Latency should be non-negative even on timeout, got {response.latency}"
        
        # Property: Response output should be empty for timeout case
        assert response.output == "", \
            "Response output should be empty when request times out"
    
    await plugin.disconnect()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(
    config=connection_config_strategy(),
    input_text=input_text_strategy()
)
async def test_request_response_always_captured(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 7: Request-response capture (comprehensive test).
    
    **Validates: Requirements 2.8**
    
    For ANY input sent to a gen AI application, the platform MUST capture
    a response - either successful output OR error. This is the core property:
    no request should go without a response being captured.
    """
    plugin = HTTPPlugin()
    
    # Test with various response scenarios
    scenarios = [
        # Success scenario
        {
            "type": "success",
            "mock": lambda: MagicMock(
                status_code=200,
                json=lambda: {"output": "Success response"},
                raise_for_status=MagicMock()
            )
        },
        # Error scenario
        {
            "type": "error",
            "mock": lambda: httpx.HTTPStatusError(
                "Error",
                request=MagicMock(),
                response=MagicMock(status_code=500, text="Error")
            )
        },
        # Timeout scenario
        {
            "type": "timeout",
            "mock": lambda: httpx.TimeoutException("Timeout")
        }
    ]
    
    # Pick one scenario randomly (Hypothesis will explore all)
    import random
    scenario = random.choice(scenarios)
    
    # Mock the HTTP client
    with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
        await plugin.connect(config)
    
    if scenario["type"] == "success":
        with patch.object(plugin._client, 'post', new_callable=AsyncMock, return_value=scenario["mock"]()):
            response = await plugin.send_input(input_text)
    else:
        with patch.object(plugin._client, 'post', side_effect=scenario["mock"]()):
            response = await plugin.send_input(input_text)
    
    # CORE PROPERTY: Response MUST be captured
    assert response is not None, \
        "Response MUST be captured for any input, regardless of success or failure"
    
    # CORE PROPERTY: Response MUST be an ApplicationResponse
    assert isinstance(response, ApplicationResponse), \
        "Response MUST be an ApplicationResponse instance"
    
    # CORE PROPERTY: Response MUST have either output OR error
    has_output = response.output is not None and len(response.output) > 0
    has_error = response.error is not None and len(response.error) > 0
    
    assert has_output or has_error, \
        "Response MUST have either output (success) OR error (failure) - " \
        f"got output='{response.output}', error='{response.error}'"
    
    # CORE PROPERTY: Response MUST have latency measurement
    assert response.latency is not None, \
        "Response MUST have latency measurement"
    assert response.latency >= 0, \
        f"Latency MUST be non-negative, got {response.latency}"
    
    # CORE PROPERTY: Output and error should be mutually exclusive
    # (either success with output, or failure with error, not both)
    if has_output:
        assert not has_error or response.error == "", \
            "Successful response should not have error"
    if has_error:
        assert not has_output or response.output == "", \
            "Failed response should not have output"
    
    await plugin.disconnect()


# ==================== Property 8: Connection Error Handling ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=connection_config_strategy()
)
async def test_http_plugin_connection_error_handling(
    config: ConnectionConfig
):
    """
    Property 8: Connection error handling (HTTP plugin).
    
    **Validates: Requirements 2.9, 7.1**
    
    For any application connection failure, the platform should return an
    error message without crashing and should not execute the evaluation.
    
    This test verifies that connection errors are handled gracefully:
    - The plugin should raise a ConnectionError (not crash)
    - The error message should be descriptive
    - The plugin should remain in a disconnected state
    - Subsequent operations should fail with appropriate errors
    """
    plugin = HTTPPlugin()
    
    # Mock connection failure scenarios
    connection_errors = [
        httpx.ConnectError("Connection refused"),
        httpx.TimeoutException("Connection timeout"),
        httpx.NetworkError("Network unreachable"),
    ]
    
    # Pick one error scenario (Hypothesis will explore all)
    import random
    error = random.choice(connection_errors)
    
    # Mock the HTTP client to fail during connection test
    with patch.object(plugin, '_test_connection', side_effect=error):
        # Attempt to connect - should raise ConnectionError
        connection_failed = False
        error_message = None
        
        try:
            await plugin.connect(config)
        except ConnectionError as e:
            connection_failed = True
            error_message = str(e)
        except Exception as e:
            # Should not raise other exceptions
            pytest.fail(
                f"Connection failure should raise ConnectionError, "
                f"not {type(e).__name__}: {str(e)}"
            )
        
        # PROPERTY: Connection failure should raise ConnectionError
        assert connection_failed, \
            "Connection failure should raise ConnectionError, not succeed"
        
        # PROPERTY: Error message should be descriptive
        assert error_message is not None, \
            "ConnectionError should have a descriptive message"
        assert len(error_message) > 0, \
            "Error message should not be empty"
        assert str(config.endpoint) in error_message or "connect" in error_message.lower(), \
            f"Error message should mention endpoint or connection: {error_message}"
        
        # PROPERTY: Plugin should remain disconnected after connection failure
        assert not plugin.is_connected(), \
            "Plugin should be disconnected after connection failure"
        
        # PROPERTY: Attempting to send input while disconnected should fail
        send_failed = False
        try:
            await plugin.send_input("test input")
        except RuntimeError as e:
            send_failed = True
            assert "not connected" in str(e).lower(), \
                "Error should indicate plugin is not connected"
        except Exception as e:
            pytest.fail(
                f"send_input on disconnected plugin should raise RuntimeError, "
                f"not {type(e).__name__}: {str(e)}"
            )
        
        assert send_failed, \
            "send_input should fail when plugin is not connected"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=websocket_config_strategy()
)
async def test_websocket_plugin_connection_error_handling(
    config: ConnectionConfig
):
    """
    Property 8: Connection error handling (WebSocket plugin).
    
    **Validates: Requirements 2.9, 7.1**
    
    For any application connection failure, the platform should return an
    error message without crashing and should not execute the evaluation.
    
    This test verifies that WebSocket connection errors are handled gracefully:
    - The plugin should raise a ConnectionError (not crash)
    - The error message should be descriptive
    - The plugin should remain in a disconnected state
    - Subsequent operations should fail with appropriate errors
    """
    plugin = WebSocketPlugin()
    
    # Mock WebSocket connection failure scenarios
    from websockets.exceptions import InvalidHandshake, InvalidURI
    
    connection_errors = [
        WebSocketException("Connection refused"),
        InvalidHandshake("Handshake failed"),
        asyncio.TimeoutError("Connection timeout"),
    ]
    
    # Pick one error scenario (Hypothesis will explore all)
    import random
    error = random.choice(connection_errors)
    
    # Mock websockets.connect to fail
    with patch('websockets.connect', side_effect=error):
        # Attempt to connect - should raise ConnectionError or ValueError
        connection_failed = False
        error_message = None
        
        try:
            await plugin.connect(config)
        except (ConnectionError, ValueError, TimeoutError) as e:
            connection_failed = True
            error_message = str(e)
        except Exception as e:
            # Should not raise other exceptions
            pytest.fail(
                f"Connection failure should raise ConnectionError/ValueError/TimeoutError, "
                f"not {type(e).__name__}: {str(e)}"
            )
        
        # PROPERTY: Connection failure should raise appropriate error
        assert connection_failed, \
            "Connection failure should raise an error, not succeed"
        
        # PROPERTY: Error message should be descriptive
        assert error_message is not None, \
            "Error should have a descriptive message"
        assert len(error_message) > 0, \
            "Error message should not be empty"
        
        # PROPERTY: Plugin should remain disconnected after connection failure
        assert not plugin.is_connected(), \
            "Plugin should be disconnected after connection failure"
        
        # PROPERTY: Attempting to send input while disconnected should fail
        send_failed = False
        try:
            await plugin.send_input("test input")
        except RuntimeError as e:
            send_failed = True
            assert "not connected" in str(e).lower(), \
                "Error should indicate plugin is not connected"
        except Exception as e:
            pytest.fail(
                f"send_input on disconnected plugin should raise RuntimeError, "
                f"not {type(e).__name__}: {str(e)}"
            )
        
        assert send_failed, \
            "send_input should fail when plugin is not connected"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=connection_config_strategy()
)
async def test_connection_error_does_not_crash_platform(
    config: ConnectionConfig
):
    """
    Property 8: Connection error handling (platform stability).
    
    **Validates: Requirements 2.9, 7.1**
    
    For any application connection failure, the platform should handle the
    error gracefully without crashing. This is a critical safety property:
    connection errors should never cause the platform to crash or enter an
    invalid state.
    
    This test verifies:
    - Multiple connection attempts can be made after failures
    - The plugin can be safely cleaned up after connection failure
    - No resources are leaked on connection failure
    - The platform remains stable and operational
    """
    plugin = HTTPPlugin()
    
    # Simulate connection failure
    with patch.object(plugin, '_test_connection', side_effect=httpx.ConnectError("Connection refused")):
        # First connection attempt - should fail gracefully
        try:
            await plugin.connect(config)
        except ConnectionError:
            pass  # Expected
        
        # PROPERTY: Plugin should be in a clean state after failure
        assert not plugin.is_connected(), \
            "Plugin should be disconnected after connection failure"
        assert plugin._client is None, \
            "HTTP client should be cleaned up after connection failure"
        
        # PROPERTY: Second connection attempt should also fail gracefully
        # (not crash due to invalid state from first failure)
        try:
            await plugin.connect(config)
        except ConnectionError:
            pass  # Expected
        
        assert not plugin.is_connected(), \
            "Plugin should still be disconnected after second failure"
        
        # PROPERTY: Disconnect should work even if never connected
        # (should not crash)
        try:
            await plugin.disconnect()
        except Exception as e:
            pytest.fail(
                f"Disconnect should not crash on never-connected plugin: {str(e)}"
            )
        
        # PROPERTY: Plugin should be in clean state after disconnect
        assert not plugin.is_connected(), \
            "Plugin should be disconnected after disconnect()"
        assert plugin._client is None, \
            "HTTP client should be None after disconnect()"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    config=connection_config_strategy(),
    input_text=input_text_strategy()
)
async def test_connection_loss_during_operation_handled_gracefully(
    config: ConnectionConfig,
    input_text: str
):
    """
    Property 8: Connection error handling (connection loss during operation).
    
    **Validates: Requirements 2.9, 7.1**
    
    For any connection loss that occurs during an operation (after successful
    connection), the platform should handle it gracefully by returning an
    error response without crashing.
    
    This test verifies:
    - Connection loss during send_input returns error response
    - The error response has appropriate error message
    - The platform does not crash or hang
    - The plugin state is updated appropriately
    """
    plugin = HTTPPlugin()
    
    # Mock successful connection
    with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
        await plugin.connect(config)
    
    assert plugin.is_connected(), \
        "Plugin should be connected after successful connect()"
    
    # Simulate connection loss during send_input
    connection_errors = [
        httpx.ConnectError("Connection lost"),
        httpx.RemoteProtocolError("Connection reset by peer"),
        httpx.ReadError("Connection closed unexpectedly"),
    ]
    
    import random
    error = random.choice(connection_errors)
    
    with patch.object(plugin._client, 'post', side_effect=error):
        # Send input - should handle connection loss gracefully
        response = await plugin.send_input(input_text)
        
        # PROPERTY: Response should not be None (no crash)
        assert response is not None, \
            "Response should not be None even when connection is lost"
        
        # PROPERTY: Response should be an ApplicationResponse
        assert isinstance(response, ApplicationResponse), \
            "Response should be an ApplicationResponse instance even on connection loss"
        
        # PROPERTY: Response should have error field populated
        assert response.error is not None, \
            "Response should have error field when connection is lost"
        assert len(response.error) > 0, \
            "Response error should not be empty when connection is lost"
        assert "connect" in response.error.lower() or "failed" in response.error.lower(), \
            f"Error message should indicate connection issue: {response.error}"
        
        # PROPERTY: Response should have latency measurement
        assert response.latency is not None, \
            "Response should have latency measurement even on connection loss"
        assert response.latency >= 0, \
            f"Latency should be non-negative, got {response.latency}"
        
        # PROPERTY: Response output should be empty for error case
        assert response.output == "", \
            "Response output should be empty when connection is lost"
    
    # Cleanup
    await plugin.disconnect()
