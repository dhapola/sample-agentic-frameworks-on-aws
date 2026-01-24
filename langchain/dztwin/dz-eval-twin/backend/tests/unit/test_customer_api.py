"""Unit tests for customer API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.customer import Customer


@pytest.fixture
def mock_customer_service():
    """Mock customer service for testing."""
    with patch("app.api.customers.get_customer_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def client():
    """Test client for API."""
    return TestClient(app)


@pytest.fixture
def sample_customer():
    """Sample customer for testing."""
    return Customer(
        id="cust_test123",
        name="Test Corp",
        contact_email="test@example.com",
        contact_phone="+1-555-0100",
        configuration={"max_runs": 5},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCreateCustomer:
    """Tests for POST /api/customers endpoint."""
    
    def test_create_customer_success(self, client, mock_customer_service, sample_customer):
        """Test successful customer creation."""
        mock_customer_service.create_customer = AsyncMock(return_value=sample_customer)
        
        response = client.post(
            "/api/customers",
            json={
                "name": "Test Corp",
                "contact_email": "test@example.com",
                "contact_phone": "+1-555-0100",
                "configuration": {"max_runs": 5}
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Corp"
        assert data["contact_email"] == "test@example.com"
        assert data["id"] == "cust_test123"
    
    def test_create_customer_validation_error(self, client, mock_customer_service):
        """Test customer creation with validation error."""
        mock_customer_service.create_customer = AsyncMock(
            side_effect=ValueError("Customer name is required")
        )
        
        response = client.post(
            "/api/customers",
            json={
                "name": "",
                "contact_email": "test@example.com"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_create_customer_missing_required_field(self, client):
        """Test customer creation with missing required field."""
        response = client.post(
            "/api/customers",
            json={
                "name": "Test Corp"
                # Missing contact_email
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data


class TestListCustomers:
    """Tests for GET /api/customers endpoint."""
    
    def test_list_customers_success(self, client, mock_customer_service, sample_customer):
        """Test successful customer listing."""
        mock_customer_service.get_all_customers = AsyncMock(
            return_value=[sample_customer]
        )
        
        response = client.get("/api/customers")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "cust_test123"
    
    def test_list_customers_empty(self, client, mock_customer_service):
        """Test listing customers when none exist."""
        mock_customer_service.get_all_customers = AsyncMock(return_value=[])
        
        response = client.get("/api/customers")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetCustomer:
    """Tests for GET /api/customers/{customer_id} endpoint."""
    
    def test_get_customer_success(self, client, mock_customer_service, sample_customer):
        """Test successful customer retrieval."""
        mock_customer_service.get_customer = AsyncMock(return_value=sample_customer)
        
        response = client.get("/api/customers/cust_test123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "cust_test123"
        assert data["name"] == "Test Corp"
    
    def test_get_customer_not_found(self, client, mock_customer_service):
        """Test getting non-existent customer."""
        mock_customer_service.get_customer = AsyncMock(return_value=None)
        
        response = client.get("/api/customers/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestUpdateCustomer:
    """Tests for PUT /api/customers/{customer_id} endpoint."""
    
    def test_update_customer_success(self, client, mock_customer_service, sample_customer):
        """Test successful customer update."""
        updated_customer = sample_customer.model_copy()
        updated_customer.name = "Updated Corp"
        
        mock_customer_service.update_customer = AsyncMock(return_value=updated_customer)
        
        response = client.put(
            "/api/customers/cust_test123",
            json={"name": "Updated Corp"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Corp"
    
    def test_update_customer_not_found(self, client, mock_customer_service):
        """Test updating non-existent customer."""
        mock_customer_service.update_customer = AsyncMock(
            side_effect=ValueError("Customer with ID nonexistent not found")
        )
        
        response = client.put(
            "/api/customers/nonexistent",
            json={"name": "Updated Corp"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_update_customer_no_fields(self, client, mock_customer_service):
        """Test updating customer with no fields provided."""
        response = client.put(
            "/api/customers/cust_test123",
            json={}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data


class TestDeleteCustomer:
    """Tests for DELETE /api/customers/{customer_id} endpoint."""
    
    def test_delete_customer_success(self, client, mock_customer_service):
        """Test successful customer deletion."""
        mock_customer_service.delete_customer = AsyncMock(return_value=None)
        
        response = client.delete("/api/customers/cust_test123")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_delete_customer_not_found(self, client, mock_customer_service):
        """Test deleting non-existent customer."""
        mock_customer_service.delete_customer = AsyncMock(
            side_effect=ValueError("Customer with ID nonexistent not found")
        )
        
        response = client.delete("/api/customers/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
