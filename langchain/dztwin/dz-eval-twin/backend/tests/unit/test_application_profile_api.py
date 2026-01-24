"""Unit tests for application profile API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig


@pytest.fixture
def mock_application_profile_service():
    """Mock application profile service for testing."""
    with patch("app.api.application_profiles.get_application_profile_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def client():
    """Test client for API."""
    return TestClient(app)


@pytest.fixture
def sample_connection_config():
    """Sample connection config for testing."""
    return ConnectionConfig(
        endpoint="https://api.example.com/v1/chat",
        authentication={"type": "bearer", "token": "sk-test"},
        timeout=30,
        retries=3,
        custom_headers={"X-Custom": "value"}
    )


@pytest.fixture
def sample_application_profile(sample_connection_config):
    """Sample application profile for testing."""
    return ApplicationProfile(
        id="app_test123",
        customer_id="cust_test456",
        name="Test Chatbot",
        type="chatbot",
        connection_config=sample_connection_config,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCreateApplicationProfile:
    """Tests for POST /api/customers/{customer_id}/application-profiles endpoint."""
    
    def test_create_application_profile_success(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test successful application profile creation."""
        mock_application_profile_service.create_application_profile = AsyncMock(
            return_value=sample_application_profile
        )
        
        response = client.post(
            "/api/customers/cust_test456/application-profiles",
            json={
                "name": "Test Chatbot",
                "type": "chatbot",
                "endpoint": "https://api.example.com/v1/chat",
                "timeout": 30,
                "retries": 3,
                "authentication": {"type": "bearer", "token": "sk-test"},
                "custom_headers": {"X-Custom": "value"}
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Chatbot"
        assert data["type"] == "chatbot"
        assert data["customer_id"] == "cust_test456"
        assert data["id"] == "app_test123"
    
    def test_create_application_profile_minimal(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test application profile creation with minimal fields."""
        mock_application_profile_service.create_application_profile = AsyncMock(
            return_value=sample_application_profile
        )
        
        response = client.post(
            "/api/customers/cust_test456/application-profiles",
            json={
                "name": "Test Chatbot",
                "type": "chatbot",
                "endpoint": "https://api.example.com/v1/chat"
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Chatbot"
    
    def test_create_application_profile_customer_not_found(
        self,
        client,
        mock_application_profile_service
    ):
        """Test application profile creation with non-existent customer."""
        mock_application_profile_service.create_application_profile = AsyncMock(
            side_effect=ValueError("Customer with ID nonexistent not found")
        )
        
        response = client.post(
            "/api/customers/nonexistent/application-profiles",
            json={
                "name": "Test Chatbot",
                "type": "chatbot",
                "endpoint": "https://api.example.com/v1/chat"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_create_application_profile_validation_error(
        self,
        client,
        mock_application_profile_service
    ):
        """Test application profile creation with validation error."""
        mock_application_profile_service.create_application_profile = AsyncMock(
            side_effect=ValueError("Profile name is required")
        )
        
        response = client.post(
            "/api/customers/cust_test456/application-profiles",
            json={
                "name": "",
                "type": "chatbot",
                "endpoint": "https://api.example.com/v1/chat"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_create_application_profile_missing_required_field(self, client):
        """Test application profile creation with missing required field."""
        response = client.post(
            "/api/customers/cust_test456/application-profiles",
            json={
                "name": "Test Chatbot",
                "type": "chatbot"
                # Missing endpoint
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_create_application_profile_invalid_type(self, client):
        """Test application profile creation with invalid type."""
        response = client.post(
            "/api/customers/cust_test456/application-profiles",
            json={
                "name": "Test App",
                "type": "invalid_type",
                "endpoint": "https://api.example.com/v1/chat"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data


class TestListCustomerApplicationProfiles:
    """Tests for GET /api/customers/{customer_id}/application-profiles endpoint."""
    
    def test_list_customer_profiles_success(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test successful listing of customer's application profiles."""
        mock_application_profile_service.get_profiles_by_customer = AsyncMock(
            return_value=[sample_application_profile]
        )
        
        response = client.get("/api/customers/cust_test456/application-profiles")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "app_test123"
        assert data[0]["customer_id"] == "cust_test456"
    
    def test_list_customer_profiles_empty(
        self,
        client,
        mock_application_profile_service
    ):
        """Test listing customer's profiles when none exist."""
        mock_application_profile_service.get_profiles_by_customer = AsyncMock(
            return_value=[]
        )
        
        response = client.get("/api/customers/cust_test456/application-profiles")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_customer_profiles_validation_error(
        self,
        client,
        mock_application_profile_service
    ):
        """Test listing profiles with validation error."""
        mock_application_profile_service.get_profiles_by_customer = AsyncMock(
            side_effect=ValueError("Customer ID is required")
        )
        
        response = client.get("/api/customers//application-profiles")
        
        # FastAPI will handle empty path parameter differently
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]


class TestGetApplicationProfile:
    """Tests for GET /api/application-profiles/{profile_id} endpoint."""
    
    def test_get_application_profile_success(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test successful application profile retrieval."""
        mock_application_profile_service.get_application_profile = AsyncMock(
            return_value=sample_application_profile
        )
        
        response = client.get("/api/application-profiles/app_test123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "app_test123"
        assert data["name"] == "Test Chatbot"
        assert data["type"] == "chatbot"
    
    def test_get_application_profile_not_found(
        self,
        client,
        mock_application_profile_service
    ):
        """Test getting non-existent application profile."""
        mock_application_profile_service.get_application_profile = AsyncMock(
            return_value=None
        )
        
        response = client.get("/api/application-profiles/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestUpdateApplicationProfile:
    """Tests for PUT /api/application-profiles/{profile_id} endpoint."""
    
    def test_update_application_profile_success(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test successful application profile update."""
        updated_profile = sample_application_profile.model_copy()
        updated_profile.name = "Updated Chatbot"
        
        mock_application_profile_service.update_application_profile = AsyncMock(
            return_value=updated_profile
        )
        
        response = client.put(
            "/api/application-profiles/app_test123",
            json={"name": "Updated Chatbot"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Chatbot"
    
    def test_update_application_profile_multiple_fields(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test updating multiple fields."""
        updated_profile = sample_application_profile.model_copy()
        updated_profile.name = "Updated Chatbot"
        
        mock_application_profile_service.update_application_profile = AsyncMock(
            return_value=updated_profile
        )
        
        response = client.put(
            "/api/application-profiles/app_test123",
            json={
                "name": "Updated Chatbot",
                "timeout": 60,
                "retries": 5
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Chatbot"
    
    def test_update_application_profile_not_found(
        self,
        client,
        mock_application_profile_service
    ):
        """Test updating non-existent application profile."""
        mock_application_profile_service.update_application_profile = AsyncMock(
            side_effect=ValueError("Application profile with ID nonexistent not found")
        )
        
        response = client.put(
            "/api/application-profiles/nonexistent",
            json={"name": "Updated Chatbot"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_update_application_profile_no_fields(
        self,
        client,
        mock_application_profile_service
    ):
        """Test updating application profile with no fields provided."""
        response = client.put(
            "/api/application-profiles/app_test123",
            json={}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_update_application_profile_validation_error(
        self,
        client,
        mock_application_profile_service
    ):
        """Test updating with validation error."""
        mock_application_profile_service.update_application_profile = AsyncMock(
            side_effect=ValueError("Timeout must be between 1 and 300 seconds")
        )
        
        response = client.put(
            "/api/application-profiles/app_test123",
            json={"timeout": 500}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"


class TestDeleteApplicationProfile:
    """Tests for DELETE /api/application-profiles/{profile_id} endpoint."""
    
    def test_delete_application_profile_success(
        self,
        client,
        mock_application_profile_service
    ):
        """Test successful application profile deletion."""
        mock_application_profile_service.delete_application_profile = AsyncMock(
            return_value=None
        )
        
        response = client.delete("/api/application-profiles/app_test123")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_delete_application_profile_not_found(
        self,
        client,
        mock_application_profile_service
    ):
        """Test deleting non-existent application profile."""
        mock_application_profile_service.delete_application_profile = AsyncMock(
            side_effect=ValueError("Application profile with ID nonexistent not found")
        )
        
        response = client.delete("/api/application-profiles/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestApplicationProfileEndpointsIntegration:
    """Integration tests for application profile endpoints."""
    
    def test_create_and_get_profile(
        self,
        client,
        mock_application_profile_service,
        sample_application_profile
    ):
        """Test creating and then retrieving a profile."""
        mock_application_profile_service.create_application_profile = AsyncMock(
            return_value=sample_application_profile
        )
        mock_application_profile_service.get_application_profile = AsyncMock(
            return_value=sample_application_profile
        )
        
        # Create profile
        create_response = client.post(
            "/api/customers/cust_test456/application-profiles",
            json={
                "name": "Test Chatbot",
                "type": "chatbot",
                "endpoint": "https://api.example.com/v1/chat"
            }
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        profile_id = create_response.json()["id"]
        
        # Get profile
        get_response = client.get(f"/api/application-profiles/{profile_id}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["id"] == profile_id
    
    def test_different_application_types(
        self,
        client,
        mock_application_profile_service,
        sample_connection_config
    ):
        """Test creating profiles with different application types."""
        app_types = ["chatbot", "rag", "agent", "workflow", "custom"]
        
        for app_type in app_types:
            profile = ApplicationProfile(
                id=f"app_{app_type}",
                customer_id="cust_test456",
                name=f"Test {app_type.title()}",
                type=app_type,
                connection_config=sample_connection_config,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            mock_application_profile_service.create_application_profile = AsyncMock(
                return_value=profile
            )
            
            response = client.post(
                "/api/customers/cust_test456/application-profiles",
                json={
                    "name": f"Test {app_type.title()}",
                    "type": app_type,
                    "endpoint": "https://api.example.com/v1/chat"
                }
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["type"] == app_type
