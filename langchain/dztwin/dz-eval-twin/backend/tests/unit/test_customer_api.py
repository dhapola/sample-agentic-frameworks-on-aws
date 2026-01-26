"""Unit tests for customer API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client for API."""
    with TestClient(app) as test_client:
        yield test_client


class TestCreateCustomer:
    """Tests for POST /api/customers endpoint."""
    
    def test_create_customer_success(self, client):
        """Test successful customer creation."""
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
        assert data["contact_phone"] == "+1-555-0100"
        assert data["configuration"] == {"max_runs": 5}
        assert "id" in data
        assert data["id"].startswith("cust_")
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_customer_validation_error(self, client):
        """Test customer creation with validation error."""
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
    
    def test_list_customers_success(self, client):
        """Test successful customer listing."""
        # Create test customers
        client.post("/api/customers", json={"name": "Customer 1", "contact_email": "c1@example.com"})
        client.post("/api/customers", json={"name": "Customer 2", "contact_email": "c2@example.com"})
        
        response = client.get("/api/customers")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        names = [c["name"] for c in data]
        assert "Customer 1" in names
        assert "Customer 2" in names
    
    def test_list_customers_empty(self, client):
        """Test listing customers when none exist."""
        response = client.get("/api/customers")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestGetCustomer:
    """Tests for GET /api/customers/{customer_id} endpoint."""
    
    def test_get_customer_success(self, client):
        """Test successful customer retrieval."""
        # Create a customer first
        create_response = client.post(
            "/api/customers",
            json={"name": "Get Test Corp", "contact_email": "gettest@example.com"}
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        customer_id = create_response.json()["id"]
        
        response = client.get(f"/api/customers/{customer_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == customer_id
        assert data["name"] == "Get Test Corp"
    
    def test_get_customer_not_found(self, client):
        """Test getting non-existent customer."""
        response = client.get("/api/customers/cust_nonexistent123")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestUpdateCustomer:
    """Tests for PUT /api/customers/{customer_id} endpoint."""
    
    def test_update_customer_success(self, client):
        """Test successful customer update."""
        # Create a customer first
        create_response = client.post(
            "/api/customers",
            json={"name": "Update Original Corp", "contact_email": "updateoriginal@example.com"}
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        customer_id = create_response.json()["id"]
        
        response = client.put(
            f"/api/customers/{customer_id}",
            json={"name": "Updated Corp"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Corp"
        assert data["contact_email"] == "updateoriginal@example.com"  # Unchanged
    
    def test_update_customer_not_found(self, client):
        """Test updating non-existent customer."""
        response = client.put(
            "/api/customers/cust_nonexistent123",
            json={"name": "Updated Corp"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_update_customer_no_fields(self, client):
        """Test updating customer with no fields provided."""
        # Create a customer first
        create_response = client.post(
            "/api/customers",
            json={"name": "No Fields Test Corp", "contact_email": "nofields@example.com"}
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        customer_id = create_response.json()["id"]
        
        response = client.put(
            f"/api/customers/{customer_id}",
            json={}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data


class TestDeleteCustomer:
    """Tests for DELETE /api/customers/{customer_id} endpoint."""
    
    def test_delete_customer_success(self, client):
        """Test successful customer deletion."""
        # Create a customer first
        create_response = client.post(
            "/api/customers",
            json={"name": "To Delete", "contact_email": "delete@example.com"}
        )
        customer_id = create_response.json()["id"]
        
        response = client.delete(f"/api/customers/{customer_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's deleted
        get_response = client.get(f"/api/customers/{customer_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_customer_not_found(self, client):
        """Test deleting non-existent customer."""
        response = client.delete("/api/customers/cust_nonexistent123")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
