"""Unit tests for ApplicationPlugin interface and base classes.

Tests the plugin interface, base implementation, and common functionality
for application connectors.
"""

import pytest
from app.connectors import (
    ApplicationPlugin,
    ApplicationResponse,
    BaseApplicationPlugin,
)
from app.models.connection_config import ConnectionConfig


class MockPlugin(BaseApplicationPlugin):
    """Mock plugin implementation for testing."""
    
    def __init__(self):
        super().__init__("mock")
        self.send_input_called = False
        self.mock_response = None
    
    async def send_input(self, input_text: str) -> ApplicationResponse:
        """Mock send_input implementation."""
        self._validate_connected()
        self._validate_input(input_text)
        self.send_input_called = True
        
        if self.mock_response:
            return self.mock_response
        
        return ApplicationResponse(
            output=f"Mock response to: {input_text}",
            latency=100.0,
            metadata={"mock": True}
        )


class TestApplicationResponse:
    """Test ApplicationResponse dataclass."""
    
    def test_create_response_with_output(self):
        """Test creating a response with output."""
        response = ApplicationResponse(
            output="Test output",
            latency=150.5
        )
        
        assert response.output == "Test output"
        assert response.latency == 150.5
        assert response.metadata is None
        assert response.error is None
    
    def test_create_response_with_metadata(self):
        """Test creating a response with metadata."""
        metadata = {"model": "gpt-4", "tokens": 100}
        response = ApplicationResponse(
            output="Test output",
            latency=200.0,
            metadata=metadata
        )
        
        assert response.metadata == metadata
        assert response.metadata["model"] == "gpt-4"
    
    def test_create_response_with_error(self):
        """Test creating a response with error."""
        response = ApplicationResponse(
            output="",
            latency=50.0,
            error="Connection timeout"
        )
        
        assert response.error == "Connection timeout"
        assert response.output == ""


class TestBaseApplicationPlugin:
    """Test BaseApplicationPlugin implementation."""
    
    @pytest.fixture
    def plugin(self):
        """Create a mock plugin instance."""
        return MockPlugin()
    
    @pytest.fixture
    def config(self):
        """Create a test connection config."""
        return ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
    
    def test_plugin_initialization(self, plugin):
        """Test plugin initializes with correct type."""
        assert plugin.type == "mock"
        assert not plugin.is_connected()
        assert plugin.config is None
    
    @pytest.mark.asyncio
    async def test_connect_stores_config(self, plugin, config):
        """Test connect stores configuration."""
        await plugin.connect(config)
        
        assert plugin.is_connected()
        assert plugin.config == config
        assert plugin.config.endpoint == config.endpoint
    
    @pytest.mark.asyncio
    async def test_connect_with_none_config_raises_error(self, plugin):
        """Test connect with None config raises ValueError."""
        with pytest.raises(ValueError, match="Connection configuration cannot be None"):
            await plugin.connect(None)
    
    @pytest.mark.asyncio
    async def test_disconnect_resets_state(self, plugin, config):
        """Test disconnect resets connection state."""
        await plugin.connect(config)
        assert plugin.is_connected()
        
        await plugin.disconnect()
        
        assert not plugin.is_connected()
        assert plugin.config is None
    
    @pytest.mark.asyncio
    async def test_send_input_when_connected(self, plugin, config):
        """Test send_input works when connected."""
        await plugin.connect(config)
        
        response = await plugin.send_input("Test input")
        
        assert plugin.send_input_called
        assert response.output == "Mock response to: Test input"
        assert response.latency == 100.0
        assert response.metadata == {"mock": True}
    
    @pytest.mark.asyncio
    async def test_send_input_when_not_connected_raises_error(self, plugin):
        """Test send_input raises error when not connected."""
        with pytest.raises(RuntimeError, match="mock plugin is not connected"):
            await plugin.send_input("Test input")
    
    @pytest.mark.asyncio
    async def test_send_input_with_none_input_raises_error(self, plugin, config):
        """Test send_input with None input raises ValueError."""
        await plugin.connect(config)
        
        with pytest.raises(ValueError, match="Input text cannot be None"):
            await plugin.send_input(None)
    
    @pytest.mark.asyncio
    async def test_send_input_with_empty_input_raises_error(self, plugin, config):
        """Test send_input with empty input raises ValueError."""
        await plugin.connect(config)
        
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await plugin.send_input("")
    
    @pytest.mark.asyncio
    async def test_send_input_with_whitespace_only_raises_error(self, plugin, config):
        """Test send_input with whitespace-only input raises ValueError."""
        await plugin.connect(config)
        
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await plugin.send_input("   ")
    
    @pytest.mark.asyncio
    async def test_send_input_with_non_string_raises_error(self, plugin, config):
        """Test send_input with non-string input raises ValueError."""
        await plugin.connect(config)
        
        with pytest.raises(ValueError, match="Input text must be a string"):
            await plugin.send_input(123)
    
    @pytest.mark.asyncio
    async def test_multiple_connect_disconnect_cycles(self, plugin, config):
        """Test multiple connect/disconnect cycles work correctly."""
        # First cycle
        await plugin.connect(config)
        assert plugin.is_connected()
        await plugin.disconnect()
        assert not plugin.is_connected()
        
        # Second cycle
        await plugin.connect(config)
        assert plugin.is_connected()
        response = await plugin.send_input("Test")
        assert response.output == "Mock response to: Test"
        await plugin.disconnect()
        assert not plugin.is_connected()
    
    @pytest.mark.asyncio
    async def test_plugin_with_custom_response(self, plugin, config):
        """Test plugin can return custom response."""
        await plugin.connect(config)
        
        custom_response = ApplicationResponse(
            output="Custom output",
            latency=250.0,
            metadata={"custom": True},
            error=None
        )
        plugin.mock_response = custom_response
        
        response = await plugin.send_input("Test")
        
        assert response == custom_response
        assert response.output == "Custom output"
        assert response.latency == 250.0
    
    @pytest.mark.asyncio
    async def test_plugin_with_error_response(self, plugin, config):
        """Test plugin can return error response."""
        await plugin.connect(config)
        
        error_response = ApplicationResponse(
            output="",
            latency=10.0,
            error="Application error occurred"
        )
        plugin.mock_response = error_response
        
        response = await plugin.send_input("Test")
        
        assert response.error == "Application error occurred"
        assert response.output == ""


class TestApplicationPluginInterface:
    """Test ApplicationPlugin abstract interface."""
    
    def test_cannot_instantiate_abstract_plugin(self):
        """Test ApplicationPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ApplicationPlugin("test")
    
    def test_subclass_must_implement_all_methods(self):
        """Test subclass must implement all abstract methods."""
        
        class IncompletePlugin(ApplicationPlugin):
            """Plugin missing required methods."""
            pass
        
        with pytest.raises(TypeError):
            IncompletePlugin("incomplete")
    
    def test_complete_subclass_can_be_instantiated(self):
        """Test complete subclass can be instantiated."""
        
        class CompletePlugin(ApplicationPlugin):
            """Complete plugin implementation."""
            
            async def connect(self, config: ConnectionConfig) -> None:
                self._connected = True
            
            async def disconnect(self) -> None:
                self._connected = False
            
            async def send_input(self, input_text: str) -> ApplicationResponse:
                return ApplicationResponse(output="test", latency=100.0)
            
            def is_connected(self) -> bool:
                return self._connected
        
        plugin = CompletePlugin("complete")
        assert plugin.type == "complete"
        assert not plugin.is_connected()
