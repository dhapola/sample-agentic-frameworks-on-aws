"""Unit tests for dataset API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.dataset import Dataset
from app.models.test_case import TestCase


@pytest.fixture
def mock_dataset_service():
    """Mock dataset service for testing."""
    with patch("app.api.datasets.get_dataset_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def client():
    """Test client for API."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_test_case():
    """Sample test case for testing."""
    return TestCase(
        id="tc_test123",
        input="What is the capital of France?",
        expected_output="Paris",
        metadata={"category": "geography"}
    )


@pytest.fixture
def sample_dataset(sample_test_case):
    """Sample dataset for testing."""
    return Dataset(
        id="dataset_test123",
        customer_id="cust_test456",
        name="Geography Questions",
        description="Test cases for geography knowledge",
        test_cases=[sample_test_case],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCreateDataset:
    """Tests for POST /api/datasets endpoint."""
    
    def test_create_dataset_success(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test successful dataset creation."""
        mock_dataset_service.create_dataset = AsyncMock(
            return_value=sample_dataset
        )
        
        response = client.post(
            "/api/datasets",
            json={
                "name": "Geography Questions",
                "description": "Test cases for geography knowledge"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Geography Questions"
        assert data["customer_id"] == "cust_test456"
        assert data["id"] == "dataset_test123"
    
    def test_create_dataset_minimal(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test dataset creation with minimal fields."""
        mock_dataset_service.create_dataset = AsyncMock(
            return_value=sample_dataset
        )
        
        response = client.post(
            "/api/datasets",
            json={
                "name": "Geography Questions"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Geography Questions"
    
    def test_create_dataset_no_customer_context(self, client):
        """Test dataset creation without customer context."""
        response = client.post(
            "/api/datasets",
            json={
                "name": "Geography Questions",
                "description": "Test cases"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UNAUTHORIZED"
    
    def test_create_dataset_validation_error(
        self,
        client,
        mock_dataset_service
    ):
        """Test dataset creation with validation error."""
        mock_dataset_service.create_dataset = AsyncMock(
            side_effect=ValueError("Dataset name is required")
        )
        
        response = client.post(
            "/api/datasets",
            json={
                "name": "",
                "description": "Test cases"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_create_dataset_missing_required_field(self, client):
        """Test dataset creation with missing required field."""
        response = client.post(
            "/api/datasets",
            json={
                "description": "Test cases"
                # Missing name
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data


class TestListDatasets:
    """Tests for GET /api/datasets endpoint."""
    
    def test_list_datasets_success(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test successful listing of datasets."""
        mock_dataset_service.get_datasets_by_customer = AsyncMock(
            return_value=[sample_dataset]
        )
        
        response = client.get(
            "/api/datasets",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "dataset_test123"
        assert data[0]["customer_id"] == "cust_test456"
    
    def test_list_datasets_empty(
        self,
        client,
        mock_dataset_service
    ):
        """Test listing datasets when none exist."""
        mock_dataset_service.get_datasets_by_customer = AsyncMock(
            return_value=[]
        )
        
        response = client.get(
            "/api/datasets",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_datasets_no_customer_context(self, client):
        """Test listing datasets without customer context."""
        response = client.get("/api/datasets")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UNAUTHORIZED"


class TestGetDataset:
    """Tests for GET /api/datasets/{dataset_id} endpoint."""
    
    def test_get_dataset_success(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test successful dataset retrieval."""
        mock_dataset_service.get_dataset = AsyncMock(
            return_value=sample_dataset
        )
        
        response = client.get(
            "/api/datasets/dataset_test123",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "dataset_test123"
        assert data["name"] == "Geography Questions"
        assert len(data["test_cases"]) == 1
    
    def test_get_dataset_not_found(
        self,
        client,
        mock_dataset_service
    ):
        """Test getting non-existent dataset."""
        mock_dataset_service.get_dataset = AsyncMock(
            return_value=None
        )
        
        response = client.get(
            "/api/datasets/nonexistent",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_get_dataset_no_customer_context(self, client):
        """Test getting dataset without customer context."""
        response = client.get("/api/datasets/dataset_test123")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data


class TestUpdateDataset:
    """Tests for PUT /api/datasets/{dataset_id} endpoint."""
    
    def test_update_dataset_success(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test successful dataset update."""
        updated_dataset = sample_dataset.model_copy()
        updated_dataset.name = "Updated Geography Questions"
        
        mock_dataset_service.update_dataset = AsyncMock(
            return_value=updated_dataset
        )
        
        response = client.put(
            "/api/datasets/dataset_test123",
            json={"name": "Updated Geography Questions"},
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Geography Questions"
    
    def test_update_dataset_multiple_fields(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test updating multiple fields."""
        updated_dataset = sample_dataset.model_copy()
        updated_dataset.name = "Updated Geography Questions"
        updated_dataset.description = "Updated description"
        
        mock_dataset_service.update_dataset = AsyncMock(
            return_value=updated_dataset
        )
        
        response = client.put(
            "/api/datasets/dataset_test123",
            json={
                "name": "Updated Geography Questions",
                "description": "Updated description"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Geography Questions"
    
    def test_update_dataset_not_found(
        self,
        client,
        mock_dataset_service
    ):
        """Test updating non-existent dataset."""
        mock_dataset_service.update_dataset = AsyncMock(
            side_effect=ValueError("Dataset with ID nonexistent not found")
        )
        
        response = client.put(
            "/api/datasets/nonexistent",
            json={"name": "Updated Dataset"},
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_update_dataset_no_fields(
        self,
        client,
        mock_dataset_service
    ):
        """Test updating dataset with no fields provided."""
        response = client.put(
            "/api/datasets/dataset_test123",
            json={},
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_update_dataset_no_customer_context(self, client):
        """Test updating dataset without customer context."""
        response = client.put(
            "/api/datasets/dataset_test123",
            json={"name": "Updated Dataset"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data


class TestDeleteDataset:
    """Tests for DELETE /api/datasets/{dataset_id} endpoint."""
    
    def test_delete_dataset_success(
        self,
        client,
        mock_dataset_service
    ):
        """Test successful dataset deletion."""
        mock_dataset_service.delete_dataset = AsyncMock(
            return_value=None
        )
        
        response = client.delete(
            "/api/datasets/dataset_test123",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_delete_dataset_not_found(
        self,
        client,
        mock_dataset_service
    ):
        """Test deleting non-existent dataset."""
        mock_dataset_service.delete_dataset = AsyncMock(
            side_effect=ValueError("Dataset with ID nonexistent not found")
        )
        
        response = client.delete(
            "/api/datasets/nonexistent",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_delete_dataset_no_customer_context(self, client):
        """Test deleting dataset without customer context."""
        response = client.delete("/api/datasets/dataset_test123")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data


class TestAddTestCase:
    """Tests for POST /api/datasets/{dataset_id}/test-cases endpoint."""
    
    def test_add_test_case_success(
        self,
        client,
        mock_dataset_service,
        sample_test_case
    ):
        """Test successful test case addition."""
        mock_dataset_service.add_test_case = AsyncMock(
            return_value=sample_test_case
        )
        
        response = client.post(
            "/api/datasets/dataset_test123/test-cases",
            json={
                "input": "What is the capital of France?",
                "expected_output": "Paris",
                "metadata": {"category": "geography"}
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input"] == "What is the capital of France?"
        assert data["expected_output"] == "Paris"
        assert data["id"] == "tc_test123"
    
    def test_add_test_case_minimal(
        self,
        client,
        mock_dataset_service,
        sample_test_case
    ):
        """Test adding test case with minimal fields."""
        mock_dataset_service.add_test_case = AsyncMock(
            return_value=sample_test_case
        )
        
        response = client.post(
            "/api/datasets/dataset_test123/test-cases",
            json={
                "input": "What is the capital of France?"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input"] == "What is the capital of France?"
    
    def test_add_test_case_dataset_not_found(
        self,
        client,
        mock_dataset_service
    ):
        """Test adding test case to non-existent dataset."""
        mock_dataset_service.add_test_case = AsyncMock(
            side_effect=ValueError("Dataset with ID nonexistent not found")
        )
        
        response = client.post(
            "/api/datasets/nonexistent/test-cases",
            json={
                "input": "What is the capital of France?"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_add_test_case_no_customer_context(self, client):
        """Test adding test case without customer context."""
        response = client.post(
            "/api/datasets/dataset_test123/test-cases",
            json={
                "input": "What is the capital of France?"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data


class TestUpdateTestCase:
    """Tests for PUT /api/datasets/{dataset_id}/test-cases/{test_case_id} endpoint."""
    
    def test_update_test_case_success(
        self,
        client,
        mock_dataset_service,
        sample_test_case
    ):
        """Test successful test case update."""
        updated_test_case = sample_test_case.model_copy()
        updated_test_case.input = "What is the capital of Germany?"
        updated_test_case.expected_output = "Berlin"
        
        mock_dataset_service.update_test_case = AsyncMock(
            return_value=updated_test_case
        )
        
        response = client.put(
            "/api/datasets/dataset_test123/test-cases/tc_test123",
            json={
                "input": "What is the capital of Germany?",
                "expected_output": "Berlin"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["input"] == "What is the capital of Germany?"
        assert data["expected_output"] == "Berlin"
    
    def test_update_test_case_single_field(
        self,
        client,
        mock_dataset_service,
        sample_test_case
    ):
        """Test updating single field of test case."""
        updated_test_case = sample_test_case.model_copy()
        updated_test_case.expected_output = "The capital of France is Paris"
        
        mock_dataset_service.update_test_case = AsyncMock(
            return_value=updated_test_case
        )
        
        response = client.put(
            "/api/datasets/dataset_test123/test-cases/tc_test123",
            json={
                "expected_output": "The capital of France is Paris"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["expected_output"] == "The capital of France is Paris"
    
    def test_update_test_case_not_found(
        self,
        client,
        mock_dataset_service
    ):
        """Test updating non-existent test case."""
        mock_dataset_service.update_test_case = AsyncMock(
            side_effect=ValueError("Test case with ID nonexistent not found")
        )
        
        response = client.put(
            "/api/datasets/dataset_test123/test-cases/nonexistent",
            json={
                "input": "Updated input"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_update_test_case_no_fields(
        self,
        client,
        mock_dataset_service
    ):
        """Test updating test case with no fields provided."""
        response = client.put(
            "/api/datasets/dataset_test123/test-cases/tc_test123",
            json={},
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_update_test_case_no_customer_context(self, client):
        """Test updating test case without customer context."""
        response = client.put(
            "/api/datasets/dataset_test123/test-cases/tc_test123",
            json={
                "input": "Updated input"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data


class TestDeleteTestCase:
    """Tests for DELETE /api/datasets/{dataset_id}/test-cases/{test_case_id} endpoint."""
    
    def test_delete_test_case_success(
        self,
        client,
        mock_dataset_service
    ):
        """Test successful test case deletion."""
        mock_dataset_service.delete_test_case = AsyncMock(
            return_value=None
        )
        
        response = client.delete(
            "/api/datasets/dataset_test123/test-cases/tc_test123",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_delete_test_case_not_found(
        self,
        client,
        mock_dataset_service
    ):
        """Test deleting non-existent test case."""
        mock_dataset_service.delete_test_case = AsyncMock(
            side_effect=ValueError("Test case with ID nonexistent not found")
        )
        
        response = client.delete(
            "/api/datasets/dataset_test123/test-cases/nonexistent",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_delete_test_case_no_customer_context(self, client):
        """Test deleting test case without customer context."""
        response = client.delete(
            "/api/datasets/dataset_test123/test-cases/tc_test123"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data


class TestDatasetEndpointsIntegration:
    """Integration tests for dataset endpoints."""
    
    def test_create_and_get_dataset(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test creating and then retrieving a dataset."""
        mock_dataset_service.create_dataset = AsyncMock(
            return_value=sample_dataset
        )
        mock_dataset_service.get_dataset = AsyncMock(
            return_value=sample_dataset
        )
        
        # Create dataset
        create_response = client.post(
            "/api/datasets",
            json={
                "name": "Geography Questions",
                "description": "Test cases for geography knowledge"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        dataset_id = create_response.json()["id"]
        
        # Get dataset
        get_response = client.get(
            f"/api/datasets/{dataset_id}",
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["id"] == dataset_id
    
    def test_add_and_update_test_case(
        self,
        client,
        mock_dataset_service,
        sample_test_case
    ):
        """Test adding and then updating a test case."""
        mock_dataset_service.add_test_case = AsyncMock(
            return_value=sample_test_case
        )
        
        updated_test_case = sample_test_case.model_copy()
        updated_test_case.expected_output = "The capital of France is Paris"
        mock_dataset_service.update_test_case = AsyncMock(
            return_value=updated_test_case
        )
        
        # Add test case
        add_response = client.post(
            "/api/datasets/dataset_test123/test-cases",
            json={
                "input": "What is the capital of France?",
                "expected_output": "Paris"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert add_response.status_code == status.HTTP_201_CREATED
        test_case_id = add_response.json()["id"]
        
        # Update test case
        update_response = client.put(
            f"/api/datasets/dataset_test123/test-cases/{test_case_id}",
            json={
                "expected_output": "The capital of France is Paris"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["expected_output"] == "The capital of France is Paris"
    
    def test_tenant_isolation(
        self,
        client,
        mock_dataset_service,
        sample_dataset
    ):
        """Test that datasets are properly isolated by customer."""
        # Customer A creates a dataset
        mock_dataset_service.create_dataset = AsyncMock(
            return_value=sample_dataset
        )
        
        create_response = client.post(
            "/api/datasets",
            json={
                "name": "Customer A Dataset",
                "description": "Test cases for customer A"
            },
            headers={"X-Customer-ID": "cust_a"}
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        dataset_id = create_response.json()["id"]
        
        # Customer B tries to access Customer A's dataset
        mock_dataset_service.get_dataset = AsyncMock(
            return_value=None  # Dataset not found for customer B
        )
        
        get_response = client.get(
            f"/api/datasets/{dataset_id}",
            headers={"X-Customer-ID": "cust_b"}
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
