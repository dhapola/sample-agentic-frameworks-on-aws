"""Unit tests for evaluation API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.evaluation_run import EvaluationRun
from app.models.metrics import AggregatedMetrics, IndividualMetrics
from app.models.response import Response


@pytest.fixture
def mock_evaluation_engine():
    """Mock evaluation engine for testing."""
    with patch("app.api.evaluations.get_evaluation_engine") as mock:
        engine = MagicMock()
        mock.return_value = engine
        yield engine


@pytest.fixture
def mock_metrics_calculator():
    """Mock metrics calculator for testing."""
    with patch("app.api.evaluations.get_metrics_calculator") as mock:
        calculator = MagicMock()
        mock.return_value = calculator
        yield calculator


@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    with patch("app.api.evaluations.get_repository") as mock:
        repository = MagicMock()
        mock.return_value = repository
        yield repository


@pytest.fixture
def client():
    """Test client for API."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_response():
    """Sample response for testing."""
    return Response(
        test_case_id="tc_test123",
        input="What is the capital of France?",
        output="Paris",
        latency=250.5,
        timestamp=datetime.utcnow(),
        error=None,
        individual_metrics=IndividualMetrics(
            accuracy=1.0,
            relevance=0.85
        )
    )


@pytest.fixture
def sample_aggregated_metrics():
    """Sample aggregated metrics for testing."""
    return AggregatedMetrics(
        average_accuracy=0.85,
        average_relevance=0.92,
        average_latency=250.5,
        median_latency=230.0,
        p95_latency=450.0,
        success_rate=0.95,
        total_test_cases=1,  # Match the number of responses in sample_evaluation_run
        failed_test_cases=0
    )


@pytest.fixture
def sample_evaluation_run(sample_response, sample_aggregated_metrics):
    """Sample evaluation run for testing."""
    return EvaluationRun(
        id="run_test123",
        customer_id="cust_test456",
        dataset_id="ds_test789",
        application_profile_id="prof_test012",
        status="completed",
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        responses=[sample_response],
        metrics=sample_aggregated_metrics
    )


class TestStartEvaluationRun:
    """Tests for POST /api/evaluations endpoint."""
    
    def test_start_evaluation_run_success(
        self,
        client,
        mock_evaluation_engine,
        mock_metrics_calculator,
        mock_repository,
        sample_evaluation_run,
        sample_aggregated_metrics
    ):
        """Test successful evaluation run start."""
        # Mock the engine to return a completed run
        mock_evaluation_engine.execute_run = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        # Mock repository to return dataset
        from app.models.dataset import Dataset
        from app.models.test_case import TestCase
        
        dataset = Dataset(
            id="ds_test789",
            customer_id="cust_test456",
            name="Test Dataset",
            description="Test",
            test_cases=[
                TestCase(
                    id="tc_test123",
                    input="What is the capital of France?",
                    expected_output="Paris"
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_repository.get_dataset_by_id = AsyncMock(return_value=dataset)
        
        # Mock metrics calculator
        mock_metrics_calculator.calculate_individual_metrics = MagicMock(
            return_value=IndividualMetrics(accuracy=1.0, relevance=0.85)
        )
        mock_metrics_calculator.aggregate_metrics = MagicMock(
            return_value=sample_aggregated_metrics
        )
        
        # Mock repository update
        mock_repository.update_evaluation_run = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_test012"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "run_test123"
        assert data["customer_id"] == "cust_test456"
        assert data["dataset_id"] == "ds_test789"
        assert data["application_profile_id"] == "prof_test012"
        assert data["status"] == "completed"
        assert "metrics" in data
        assert data["metrics"]["average_accuracy"] == 0.85
    
    def test_start_evaluation_run_no_customer_context(self, client):
        """Test starting evaluation run without customer context."""
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_test012"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UNAUTHORIZED"
    
    def test_start_evaluation_run_dataset_not_found(
        self,
        client,
        mock_evaluation_engine
    ):
        """Test starting evaluation run with non-existent dataset."""
        mock_evaluation_engine.execute_run = AsyncMock(
            side_effect=ValueError("Dataset ds_nonexistent not found for customer cust_test456")
        )
        
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_nonexistent",
                "application_profile_id": "prof_test012"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_start_evaluation_run_profile_not_found(
        self,
        client,
        mock_evaluation_engine
    ):
        """Test starting evaluation run with non-existent application profile."""
        mock_evaluation_engine.execute_run = AsyncMock(
            side_effect=ValueError("Application profile prof_nonexistent not found")
        )
        
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_nonexistent"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_start_evaluation_run_connection_error(
        self,
        client,
        mock_evaluation_engine
    ):
        """Test starting evaluation run with connection error."""
        mock_evaluation_engine.execute_run = AsyncMock(
            side_effect=ConnectionError("Failed to connect to application")
        )
        
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_test012"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "Failed to connect to application" in data["error"]["message"]
    
    def test_start_evaluation_run_missing_required_field(self, client):
        """Test starting evaluation run with missing required field."""
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789"
                # Missing application_profile_id
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_start_evaluation_run_wrong_customer(
        self,
        client,
        mock_evaluation_engine
    ):
        """Test starting evaluation run with dataset from different customer."""
        mock_evaluation_engine.execute_run = AsyncMock(
            side_effect=ValueError("Dataset ds_test789 does not belong to customer cust_other")
        )
        
        response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_test012"
            },
            headers={"X-Customer-ID": "cust_other"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data


class TestListEvaluationRuns:
    """Tests for GET /api/evaluations endpoint."""
    
    def test_list_evaluation_runs_success(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test successful listing of evaluation runs."""
        mock_repository.get_evaluation_runs = AsyncMock(
            return_value=[sample_evaluation_run]
        )
        
        response = client.get(
            "/api/evaluations",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "run_test123"
        assert data[0]["customer_id"] == "cust_test456"
        # Summary response should not include full responses
        assert "responses" not in data[0] or len(data[0].get("responses", [])) == 0
    
    def test_list_evaluation_runs_empty(
        self,
        client,
        mock_repository
    ):
        """Test listing evaluation runs when none exist."""
        mock_repository.get_evaluation_runs = AsyncMock(
            return_value=[]
        )
        
        response = client.get(
            "/api/evaluations",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_evaluation_runs_no_customer_context(self, client):
        """Test listing evaluation runs without customer context."""
        response = client.get("/api/evaluations")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UNAUTHORIZED"
    
    def test_list_evaluation_runs_multiple(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test listing multiple evaluation runs."""
        run1 = sample_evaluation_run
        run2 = sample_evaluation_run.model_copy()
        run2.id = "run_test456"
        run2.dataset_id = "ds_test999"
        
        mock_repository.get_evaluation_runs = AsyncMock(
            return_value=[run1, run2]
        )
        
        response = client.get(
            "/api/evaluations",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "run_test123"
        assert data[1]["id"] == "run_test456"


class TestGetEvaluationRun:
    """Tests for GET /api/evaluations/{run_id} endpoint."""
    
    def test_get_evaluation_run_success(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test successful evaluation run retrieval."""
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        response = client.get(
            "/api/evaluations/run_test123",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "run_test123"
        assert data["customer_id"] == "cust_test456"
        assert "responses" in data
        assert len(data["responses"]) == 1
        assert "metrics" in data
    
    def test_get_evaluation_run_not_found(
        self,
        client,
        mock_repository
    ):
        """Test getting non-existent evaluation run."""
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            return_value=None
        )
        
        response = client.get(
            "/api/evaluations/run_nonexistent",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_get_evaluation_run_no_customer_context(self, client):
        """Test getting evaluation run without customer context."""
        response = client.get("/api/evaluations/run_test123")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
    
    def test_get_evaluation_run_with_responses(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test getting evaluation run with multiple responses."""
        # Add more responses
        response2 = Response(
            test_case_id="tc_test456",
            input="What is 2+2?",
            output="4",
            latency=150.0,
            timestamp=datetime.utcnow(),
            error=None,
            individual_metrics=IndividualMetrics(accuracy=1.0, relevance=1.0)
        )
        sample_evaluation_run.responses.append(response2)
        
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        response = client.get(
            "/api/evaluations/run_test123",
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["responses"]) == 2


class TestCompareRuns:
    """Tests for POST /api/evaluations/compare endpoint."""
    
    def test_compare_runs_success(
        self,
        client,
        mock_repository,
        sample_evaluation_run,
        sample_aggregated_metrics
    ):
        """Test successful run comparison."""
        run1 = sample_evaluation_run
        run2 = sample_evaluation_run.model_copy()
        run2.id = "run_test456"
        run2.metrics = AggregatedMetrics(
            average_accuracy=0.90,
            average_relevance=0.88,
            average_latency=300.0,
            median_latency=280.0,
            p95_latency=500.0,
            success_rate=0.98,
            total_test_cases=20,
            failed_test_cases=0
        )
        
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            side_effect=[run1, run2]
        )
        
        response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": ["run_test123", "run_test456"]
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "runs" in data
        assert len(data["runs"]) == 2
        assert data["runs"][0]["run_id"] == "run_test123"
        assert data["runs"][1]["run_id"] == "run_test456"
        assert data["runs"][0]["metrics"]["average_accuracy"] == 0.85
        assert data["runs"][1]["metrics"]["average_accuracy"] == 0.90
    
    def test_compare_runs_single_run(
        self,
        client,
        mock_repository
    ):
        """Test comparison with only one run (should fail)."""
        response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": ["run_test123"]
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_compare_runs_not_found(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test comparison with non-existent run."""
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            side_effect=[sample_evaluation_run, None]
        )
        
        response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": ["run_test123", "run_nonexistent"]
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_compare_runs_no_customer_context(self, client):
        """Test comparison without customer context."""
        response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": ["run_test123", "run_test456"]
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
    
    def test_compare_runs_empty_list(self, client):
        """Test comparison with empty run list."""
        response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": []
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
    
    def test_compare_runs_three_runs(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test comparison with three runs."""
        run1 = sample_evaluation_run
        run2 = sample_evaluation_run.model_copy()
        run2.id = "run_test456"
        run3 = sample_evaluation_run.model_copy()
        run3.id = "run_test789"
        
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            side_effect=[run1, run2, run3]
        )
        
        response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": ["run_test123", "run_test456", "run_test789"]
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["runs"]) == 3


class TestEvaluationEndpointsIntegration:
    """Integration tests for evaluation endpoints."""
    
    def test_start_and_get_evaluation_run(
        self,
        client,
        mock_evaluation_engine,
        mock_metrics_calculator,
        mock_repository,
        sample_evaluation_run,
        sample_aggregated_metrics
    ):
        """Test starting and then retrieving an evaluation run."""
        # Mock engine for start
        mock_evaluation_engine.execute_run = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        # Mock repository for dataset
        from app.models.dataset import Dataset
        from app.models.test_case import TestCase
        
        dataset = Dataset(
            id="ds_test789",
            customer_id="cust_test456",
            name="Test Dataset",
            description="Test",
            test_cases=[
                TestCase(
                    id="tc_test123",
                    input="What is the capital of France?",
                    expected_output="Paris"
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_repository.get_dataset_by_id = AsyncMock(return_value=dataset)
        
        # Mock metrics
        mock_metrics_calculator.calculate_individual_metrics = MagicMock(
            return_value=IndividualMetrics(accuracy=1.0, relevance=0.85)
        )
        mock_metrics_calculator.aggregate_metrics = MagicMock(
            return_value=sample_aggregated_metrics
        )
        mock_repository.update_evaluation_run = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        # Start evaluation run
        start_response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_test012"
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert start_response.status_code == status.HTTP_201_CREATED
        run_id = start_response.json()["id"]
        
        # Mock repository for get
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        # Get evaluation run
        get_response = client.get(
            f"/api/evaluations/{run_id}",
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["id"] == run_id
    
    def test_list_and_compare_runs(
        self,
        client,
        mock_repository,
        sample_evaluation_run
    ):
        """Test listing runs and then comparing them."""
        run1 = sample_evaluation_run
        run2 = sample_evaluation_run.model_copy()
        run2.id = "run_test456"
        
        # Mock list
        mock_repository.get_evaluation_runs = AsyncMock(
            return_value=[run1, run2]
        )
        
        # List runs
        list_response = client.get(
            "/api/evaluations",
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert list_response.status_code == status.HTTP_200_OK
        runs = list_response.json()
        assert len(runs) == 2
        
        # Mock compare
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            side_effect=[run1, run2]
        )
        
        # Compare runs
        compare_response = client.post(
            "/api/evaluations/compare",
            json={
                "run_ids": [runs[0]["id"], runs[1]["id"]]
            },
            headers={"X-Customer-ID": "cust_test456"}
        )
        assert compare_response.status_code == status.HTTP_200_OK
        comparison = compare_response.json()
        assert len(comparison["runs"]) == 2
    
    def test_tenant_isolation(
        self,
        client,
        mock_evaluation_engine,
        mock_repository,
        sample_evaluation_run
    ):
        """Test that evaluation runs are properly isolated by customer."""
        # Customer A starts an evaluation run
        mock_evaluation_engine.execute_run = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        from app.models.dataset import Dataset
        from app.models.test_case import TestCase
        
        dataset = Dataset(
            id="ds_test789",
            customer_id="cust_a",
            name="Test Dataset",
            description="Test",
            test_cases=[
                TestCase(
                    id="tc_test123",
                    input="Test",
                    expected_output="Test"
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_repository.get_dataset_by_id = AsyncMock(return_value=dataset)
        mock_repository.update_evaluation_run = AsyncMock(
            return_value=sample_evaluation_run
        )
        
        start_response = client.post(
            "/api/evaluations",
            json={
                "dataset_id": "ds_test789",
                "application_profile_id": "prof_test012"
            },
            headers={"X-Customer-ID": "cust_a"}
        )
        assert start_response.status_code == status.HTTP_201_CREATED
        run_id = start_response.json()["id"]
        
        # Customer B tries to access Customer A's evaluation run
        mock_repository.get_evaluation_run_by_id = AsyncMock(
            return_value=None  # Run not found for customer B
        )
        
        get_response = client.get(
            f"/api/evaluations/{run_id}",
            headers={"X-Customer-ID": "cust_b"}
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
