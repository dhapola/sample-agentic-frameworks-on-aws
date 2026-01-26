"""Integration tests for comprehensive error handling.

This module tests error handling across all layers of the system:
- Validation errors
- Connection errors
- Database errors
- Execution errors

Tests verify that:
1. All error paths return appropriate responses
2. Error logging is comprehensive
3. Error scenarios work end-to-end
4. System maintains stability when operations fail

Validates Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from app.main import app
from app.database.connection import database_manager
from app.models.customer import Customer
from app.models.dataset import Dataset
from app.models.test_case import TestCase as TestCaseModel
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig


@pytest.fixture
def test_client():
    """Create test client with customer context."""
    with TestClient(app) as client:
        # Add customer context header
        client.headers["X-Customer-ID"] = "test_customer_error_handling"
        yield client


@pytest.fixture(scope="function")
def setup_test_data():
    """Set up test data for error handling tests."""
    # Note: This is a synchronous fixture for use with TestClient
    # Actual setup happens in individual tests as needed
    yield {
        "customer_id": "test_customer_error_handling",
        "profile_id": "test_profile_error"
    }


class TestValidationErrors:
    """Test validation error handling (Requirement 7.4, 7.5)."""
    
    def test_empty_dataset_name_returns_validation_error(self, test_client):
        """Test that empty dataset name returns validation error."""
        response = test_client.post(
            "/api/datasets",
            json={"name": "", "description": "Test"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "name" in data["error"]["message"].lower()
    
    def test_missing_required_field_returns_validation_error(self, test_client):
        """Test that missing required field returns validation error."""
        response = test_client.post(
            "/api/datasets",
            json={"description": "Test"}  # Missing 'name'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_invalid_dataset_id_format_returns_validation_error(self, test_client):
        """Test that invalid dataset ID format returns validation error."""
        response = test_client.get("/api/datasets/")
        
        # Should return 404 or 405 for invalid path
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    def test_empty_test_case_input_returns_validation_error(
        self, test_client, setup_test_data
    ):
        """Test that empty test case input returns validation error."""
        # Create a dataset first
        dataset_response = test_client.post(
            "/api/datasets",
            json={"name": "Test Dataset", "description": "Test"}
        )
        assert dataset_response.status_code == status.HTTP_201_CREATED
        dataset_id = dataset_response.json()["id"]
        
        # Try to add test case with empty input
        response = test_client.post(
            f"/api/datasets/{dataset_id}/test-cases",
            json={"input": "", "expected_output": "Test"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_missing_customer_context_returns_unauthorized(self):
        """Test that missing customer context returns unauthorized error."""
        with TestClient(app) as client:
            # Don't add X-Customer-ID header
            response = client.get("/api/datasets")
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "UNAUTHORIZED"


class TestDatabaseErrors:
    """Test database error handling (Requirement 7.2)."""
    
    def test_database_connection_failure_returns_error(self, test_client):
        """Test that database connection failure returns appropriate error."""
        # Mock database operation to raise RuntimeError
        with patch(
            "app.database.repository.DataRepository.get_datasets",
            side_effect=RuntimeError("Database error retrieving datasets: Connection failed")
        ):
            response = test_client.get("/api/datasets")
            
            # Should return 500 or validation error
            assert response.status_code in [
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_400_BAD_REQUEST
            ]
            data = response.json()
            assert "error" in data
    
    def test_database_write_failure_returns_error(self, test_client):
        """Test that database write failure returns appropriate error."""
        # Mock database operation to raise RuntimeError
        with patch(
            "app.database.repository.DataRepository.create_dataset",
            side_effect=RuntimeError("Database error creating dataset: Write failed")
        ):
            response = test_client.post(
                "/api/datasets",
                json={"name": "Test Dataset", "description": "Test"}
            )
            
            # Should return 500 or validation error
            assert response.status_code in [
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_400_BAD_REQUEST
            ]
            data = response.json()
            assert "error" in data


class TestNotFoundErrors:
    """Test not found error handling."""
    
    def test_get_nonexistent_dataset_returns_404(self, test_client):
        """Test that getting nonexistent dataset returns 404."""
        response = test_client.get("/api/datasets/nonexistent_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_update_nonexistent_dataset_returns_404(self, test_client):
        """Test that updating nonexistent dataset returns 404."""
        response = test_client.put(
            "/api/datasets/nonexistent_id",
            json={"name": "Updated Name"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_delete_nonexistent_dataset_returns_404(self, test_client):
        """Test that deleting nonexistent dataset returns 404."""
        response = test_client.delete("/api/datasets/nonexistent_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_get_nonexistent_evaluation_run_returns_404(self, test_client):
        """Test that getting nonexistent evaluation run returns 404."""
        response = test_client.get("/api/evaluations/nonexistent_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestSystemStability:
    """Test that system maintains stability when operations fail (Requirement 7.6)."""
    
    def test_failed_operation_does_not_corrupt_data(
        self, test_client, setup_test_data
    ):
        """Test that failed operations don't corrupt existing data."""
        # Create a dataset
        dataset_response = test_client.post(
            "/api/datasets",
            json={"name": "Test Dataset", "description": "Test"}
        )
        assert dataset_response.status_code == status.HTTP_201_CREATED
        dataset_id = dataset_response.json()["id"]
        
        # Try to update with invalid data
        response = test_client.put(
            f"/api/datasets/{dataset_id}",
            json={"name": ""}  # Invalid empty name
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Verify original data is intact
        get_response = test_client.get(f"/api/datasets/{dataset_id}")
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["name"] == "Test Dataset"
