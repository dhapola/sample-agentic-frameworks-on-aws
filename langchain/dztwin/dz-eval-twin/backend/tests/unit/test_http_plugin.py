"""Unit tests for HTTP/REST plugin.

Tests the HTTP plugin implementation including connection management,
request/response handling, authentication, timeout, retry logic, and
error handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.http_plugin import HTTPPlugin
from app.connectors.plugin import ApplicationResponse
from app.models.connection_config import ConnectionConfig


class TestHTTPPluginInitialization:
    """Test HTTP plugin initialization."""
    
    def test_plugin_initialization(self):
        """Test plugin initializes with correct type."""
        plugin = HTTPPlugin()
        
        assert plugin.type == "http"
        assert not plugin.is_connected()
        assert plugin.config is None
        assert plugin._client is None
    
    def test_plugin_type_is_http(self):
        """Test plugin type is 'http'."""
        plugin = HTTPPlugin()
        assert plugin.type == "http"


class TestHTTPPluginConnection:
    """Test HTTP plugin connection management."""
    
    @pytest.fixture
    def plugin(self):
        """Create HTTP plugin instance."""
        return HTTPPlugin()
    
    @pytest.fixture
    def basic_config(self):
        """Create basic connection config."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    def config_with_bearer_auth(self):
        """Create config with Bearer authentication."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            authentication={
                "type": "bearer",
                "token": "sk-test-token-123"
            },
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    def config_with_api_key_auth(self):
        """Create config with API Key authentication."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            authentication={
                "type": "api_key",
                "api_key": "test-api-key-456",
                "header_name": "X-API-Key"
            },
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    def config_with_basic_auth(self):
        """Create config with Basic authentication."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            authentication={
                "type": "basic",
                "username": "testuser",
                "password": "testpass"
            },
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    def config_with_custom_headers(self):
        """Create config with custom headers."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            custom_headers={
                "X-Custom-Header": "custom-value",
                "X-Request-ID": "req-123"
            },
            timeout=30,
            retries=3
        )
    
    @pytest.mark.asyncio
    async def test_connect_creates_http_client(self, plugin, basic_config):
        """Test connect creates HTTP client."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(basic_config)
            
            assert plugin.is_connected()
            assert plugin._client is not None
            assert isinstance(plugin._client, httpx.AsyncClient)
            
            await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_with_bearer_auth_sets_headers(self, plugin, config_with_bearer_auth):
        """Test connect with Bearer auth sets Authorization header."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config_with_bearer_auth)
            
            headers = plugin._client.headers
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer sk-test-token-123"
            
            await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_with_api_key_auth_sets_headers(self, plugin, config_with_api_key_auth):
        """Test connect with API Key auth sets custom header."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config_with_api_key_auth)
            
            headers = plugin._client.headers
            assert "X-API-Key" in headers
            assert headers["X-API-Key"] == "test-api-key-456"
            
            await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_with_custom_headers_sets_headers(self, plugin, config_with_custom_headers):
        """Test connect with custom headers sets them correctly."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config_with_custom_headers)
            
            headers = plugin._client.headers
            assert "X-Custom-Header" in headers
            assert headers["X-Custom-Header"] == "custom-value"
            assert "X-Request-ID" in headers
            assert headers["X-Request-ID"] == "req-123"
            
            await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_sets_timeout(self, plugin, basic_config):
        """Test connect sets timeout configuration."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(basic_config)
            
            assert plugin._client.timeout.read == 30.0
            
            await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_with_none_config_raises_error(self, plugin):
        """Test connect with None config raises ValueError."""
        with pytest.raises(ValueError, match="Connection configuration cannot be None"):
            await plugin.connect(None)
    
    @pytest.mark.asyncio
    async def test_connect_failure_cleans_up_client(self, plugin, basic_config):
        """Test connect failure cleans up HTTP client."""
        with patch.object(plugin, '_test_connection', side_effect=ConnectionError("Test error")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await plugin.connect(basic_config)
            
            assert not plugin.is_connected()
            assert plugin._client is None
    
    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, plugin, basic_config):
        """Test disconnect closes HTTP client."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(basic_config)
            assert plugin.is_connected()
            
            await plugin.disconnect()
            
            assert not plugin.is_connected()
            assert plugin._client is None
    
    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, plugin):
        """Test disconnect when not connected doesn't raise error."""
        await plugin.disconnect()
        assert not plugin.is_connected()
    
    @pytest.mark.asyncio
    async def test_is_connected_returns_false_initially(self, plugin):
        """Test is_connected returns False initially."""
        assert not plugin.is_connected()
    
    @pytest.mark.asyncio
    async def test_is_connected_returns_true_after_connect(self, plugin, basic_config):
        """Test is_connected returns True after connect."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(basic_config)
            assert plugin.is_connected()
            await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_multiple_connect_disconnect_cycles(self, plugin, basic_config):
        """Test multiple connect/disconnect cycles work correctly."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            # First cycle
            await plugin.connect(basic_config)
            assert plugin.is_connected()
            await plugin.disconnect()
            assert not plugin.is_connected()
            
            # Second cycle
            await plugin.connect(basic_config)
            assert plugin.is_connected()
            await plugin.disconnect()
            assert not plugin.is_connected()


class TestHTTPPluginSendInput:
    """Test HTTP plugin send_input functionality."""
    
    @pytest.fixture
    def plugin(self):
        """Create HTTP plugin instance."""
        return HTTPPlugin()
    
    @pytest.fixture
    def config(self):
        """Create connection config."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    async def connected_plugin(self, plugin, config):
        """Create and connect plugin."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config)
        yield plugin
        await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_send_input_when_not_connected_raises_error(self, plugin):
        """Test send_input raises error when not connected."""
        with pytest.raises(RuntimeError, match="http plugin is not connected"):
            await plugin.send_input("Test input")
    
    @pytest.mark.asyncio
    async def test_send_input_with_none_input_raises_error(self, connected_plugin):
        """Test send_input with None input raises ValueError."""
        with pytest.raises(ValueError, match="Input text cannot be None"):
            await connected_plugin.send_input(None)
    
    @pytest.mark.asyncio
    async def test_send_input_with_empty_input_raises_error(self, connected_plugin):
        """Test send_input with empty input raises ValueError."""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await connected_plugin.send_input("")
    
    @pytest.mark.asyncio
    async def test_send_input_with_whitespace_only_raises_error(self, connected_plugin):
        """Test send_input with whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await connected_plugin.send_input("   ")
    
    @pytest.mark.asyncio
    async def test_send_input_successful_response(self, connected_plugin):
        """Test send_input with successful response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "output": "This is the generated response",
            "metadata": {"model": "gpt-4", "tokens": 50}
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(connected_plugin._client, 'post', new_callable=AsyncMock, return_value=mock_response):
            response = await connected_plugin.send_input("Test input")
            
            assert isinstance(response, ApplicationResponse)
            assert response.output == "This is the generated response"
            assert response.latency > 0
            assert response.metadata == {"model": "gpt-4", "tokens": 50}
            assert response.error is None
    
    @pytest.mark.asyncio
    async def test_send_input_measures_latency(self, connected_plugin):
        """Test send_input measures latency correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "Response"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        async def delayed_post(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return mock_response
        
        with patch.object(connected_plugin._client, 'post', side_effect=delayed_post):
            response = await connected_plugin.send_input("Test input")
            
            # Latency should be at least 100ms
            assert response.latency >= 100
            # But not too much more (allow 50ms overhead)
            assert response.latency < 200
    
    @pytest.mark.asyncio
    async def test_send_input_sends_correct_payload(self, connected_plugin):
        """Test send_input sends correct JSON payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "Response"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        mock_post = AsyncMock(return_value=mock_response)
        
        with patch.object(connected_plugin._client, 'post', mock_post):
            await connected_plugin.send_input("Test input text")
            
            # Verify POST was called with correct payload
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs['json'] == {"input": "Test input text"}
    
    @pytest.mark.asyncio
    async def test_send_input_with_response_missing_output(self, connected_plugin):
        """Test send_input handles response missing output field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"metadata": {"info": "test"}}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(connected_plugin._client, 'post', new_callable=AsyncMock, return_value=mock_response):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert response.error == "Response missing 'output' field"
    
    @pytest.mark.asyncio
    async def test_send_input_with_error_in_response(self, connected_plugin):
        """Test send_input handles error in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "output": "",
            "error": "Application error occurred"
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(connected_plugin._client, 'post', new_callable=AsyncMock, return_value=mock_response):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert response.error == "Application error occurred"


class TestHTTPPluginErrorHandling:
    """Test HTTP plugin error handling."""
    
    @pytest.fixture
    def plugin(self):
        """Create HTTP plugin instance."""
        return HTTPPlugin()
    
    @pytest.fixture
    def config(self):
        """Create connection config."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    async def connected_plugin(self, plugin, config):
        """Create and connect plugin."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config)
        yield plugin
        await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_send_input_handles_timeout(self, connected_plugin):
        """Test send_input handles timeout errors."""
        with patch.object(
            connected_plugin._client,
            'post',
            side_effect=httpx.TimeoutException("Request timeout")
        ):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "timeout" in response.error.lower()
            assert response.latency > 0
    
    @pytest.mark.asyncio
    async def test_send_input_handles_http_500_error(self, connected_plugin):
        """Test send_input handles HTTP 500 errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(connected_plugin._client, 'post', side_effect=error):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "HTTP 500" in response.error
            assert response.latency > 0
    
    @pytest.mark.asyncio
    async def test_send_input_handles_http_404_error(self, connected_plugin):
        """Test send_input handles HTTP 404 errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        error = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(connected_plugin._client, 'post', side_effect=error):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "HTTP 404" in response.error
    
    @pytest.mark.asyncio
    async def test_send_input_handles_connection_error(self, connected_plugin):
        """Test send_input handles connection errors."""
        with patch.object(
            connected_plugin._client,
            'post',
            side_effect=httpx.ConnectError("Connection refused")
        ):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "failed to connect" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_send_input_handles_generic_exception(self, connected_plugin):
        """Test send_input handles generic exceptions."""
        with patch.object(
            connected_plugin._client,
            'post',
            side_effect=Exception("Unexpected error")
        ):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "Request failed" in response.error


class TestHTTPPluginRetryLogic:
    """Test HTTP plugin retry logic."""
    
    @pytest.fixture
    def plugin(self):
        """Create HTTP plugin instance."""
        return HTTPPlugin()
    
    @pytest.fixture
    def config(self):
        """Create connection config with retries."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
    
    @pytest.fixture
    async def connected_plugin(self, plugin, config):
        """Create and connect plugin."""
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config)
        yield plugin
        await plugin.disconnect()
    
    @pytest.mark.asyncio
    async def test_retry_on_500_error(self, connected_plugin):
        """Test retry logic on HTTP 500 errors."""
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        mock_response_error.text = "Server Error"
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"output": "Success"}
        mock_response_success.raise_for_status = MagicMock()
        
        # First call fails with 500, second succeeds
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response_error
        )
        
        mock_post = AsyncMock(side_effect=[error, mock_response_success])
        
        with patch.object(connected_plugin._client, 'post', mock_post):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                response = await connected_plugin.send_input("Test input")
                
                assert response.output == "Success"
                assert response.error is None
                # Should have been called twice (initial + 1 retry)
                assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_400_error(self, connected_plugin):
        """Test no retry on HTTP 400 errors (client errors)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        error = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=mock_response
        )
        
        mock_post = AsyncMock(side_effect=error)
        
        with patch.object(connected_plugin._client, 'post', mock_post):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "HTTP 400" in response.error
            # Should only be called once (no retries on 4xx)
            assert mock_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, connected_plugin):
        """Test retry logic on connection errors."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": "Success"}
        mock_response.raise_for_status = MagicMock()
        
        # First two calls fail with connection error, third succeeds
        mock_post = AsyncMock(side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            mock_response
        ])
        
        with patch.object(connected_plugin._client, 'post', mock_post):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                response = await connected_plugin.send_input("Test input")
                
                assert response.output == "Success"
                assert response.error is None
                # Should have been called 3 times (initial + 2 retries)
                assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, connected_plugin):
        """Test behavior when max retries exceeded."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )
        
        # Always fail
        mock_post = AsyncMock(side_effect=error)
        
        with patch.object(connected_plugin._client, 'post', mock_post):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                response = await connected_plugin.send_input("Test input")
                
                assert response.output == ""
                assert "HTTP 500" in response.error
                # Should have been called 4 times (initial + 3 retries)
                assert mock_post.call_count == 4
    
    @pytest.mark.asyncio
    async def test_no_retry_on_timeout(self, connected_plugin):
        """Test no retry on timeout errors."""
        mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        
        with patch.object(connected_plugin._client, 'post', mock_post):
            response = await connected_plugin.send_input("Test input")
            
            assert response.output == ""
            assert "timeout" in response.error.lower()
            # Should only be called once (no retries on timeout)
            assert mock_post.call_count == 1


class TestHTTPPluginAuthentication:
    """Test HTTP plugin authentication methods."""
    
    @pytest.fixture
    def plugin(self):
        """Create HTTP plugin instance."""
        return HTTPPlugin()
    
    @pytest.mark.asyncio
    async def test_basic_auth_in_request(self, plugin):
        """Test Basic authentication is passed in request."""
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            authentication={
                "type": "basic",
                "username": "testuser",
                "password": "testpass"
            },
            timeout=30,
            retries=0
        )
        
        with patch.object(plugin, '_test_connection', new_callable=AsyncMock):
            await plugin.connect(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": "Success"}
        mock_response.raise_for_status = MagicMock()
        
        mock_post = AsyncMock(return_value=mock_response)
        
        with patch.object(plugin._client, 'post', mock_post):
            await plugin.send_input("Test input")
            
            # Verify auth parameter was passed
            call_kwargs = mock_post.call_args.kwargs
            assert 'auth' in call_kwargs
            auth = call_kwargs['auth']
            assert isinstance(auth, httpx.BasicAuth)
        
        await plugin.disconnect()


class TestHTTPPluginBuildHeaders:
    """Test HTTP plugin header building."""
    
    def test_build_headers_default(self):
        """Test building default headers."""
        plugin = HTTPPlugin()
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
        
        headers = plugin._build_headers(config)
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
    
    def test_build_headers_with_bearer_auth(self):
        """Test building headers with Bearer authentication."""
        plugin = HTTPPlugin()
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            authentication={
                "type": "bearer",
                "token": "test-token"
            },
            timeout=30,
            retries=3
        )
        
        headers = plugin._build_headers(config)
        
        assert headers["Authorization"] == "Bearer test-token"
    
    def test_build_headers_with_api_key_auth(self):
        """Test building headers with API Key authentication."""
        plugin = HTTPPlugin()
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            authentication={
                "type": "api_key",
                "api_key": "test-key",
                "header_name": "X-API-Key"
            },
            timeout=30,
            retries=3
        )
        
        headers = plugin._build_headers(config)
        
        assert headers["X-API-Key"] == "test-key"
    
    def test_build_headers_with_custom_headers(self):
        """Test building headers with custom headers."""
        plugin = HTTPPlugin()
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            custom_headers={
                "X-Custom": "value",
                "X-Request-ID": "123"
            },
            timeout=30,
            retries=3
        )
        
        headers = plugin._build_headers(config)
        
        assert headers["X-Custom"] == "value"
        assert headers["X-Request-ID"] == "123"
    
    def test_build_headers_custom_overrides_default(self):
        """Test custom headers override default headers."""
        plugin = HTTPPlugin()
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            custom_headers={
                "Content-Type": "application/xml"
            },
            timeout=30,
            retries=3
        )
        
        headers = plugin._build_headers(config)
        
        assert headers["Content-Type"] == "application/xml"
