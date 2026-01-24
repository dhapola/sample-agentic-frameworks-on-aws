"""Basic unit tests for Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    Customer,
    ApplicationProfile,
    ConnectionConfig,
    Dataset,
    TestCase,
    EvaluationRun,
    Response,
    IndividualMetrics,
    AggregatedMetrics,
)


class TestCustomerModel:
    """Test Customer model validation."""
    
    def test_valid_customer(self):
        """Test creating a valid customer."""
        customer = Customer(
            id="cust_123",
            name="Acme Corp",
            contact_email="admin@acme.com",
            contact_phone="+1-555-0100"
        )
        assert customer.id == "cust_123"
        assert customer.name == "Acme Corp"
        assert customer.contact_email == "admin@acme.com"
        assert customer.contact_phone == "+1-555-0100"
    
    def test_customer_name_validation(self):
        """Test customer name cannot be empty or whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                id="cust_123",
                name="   ",
                contact_email="admin@acme.com"
            )
        assert "Customer name cannot be empty" in str(exc_info.value)
    
    def test_customer_email_validation(self):
        """Test customer email must be valid."""
        with pytest.raises(ValidationError):
            Customer(
                id="cust_123",
                name="Acme Corp",
                contact_email="invalid-email"
            )


class TestConnectionConfigModel:
    """Test ConnectionConfig model validation."""
    
    def test_valid_connection_config(self):
        """Test creating a valid connection config."""
        config = ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        )
        assert str(config.endpoint) == "https://api.example.com/v1/chat"
        assert config.timeout == 30
        assert config.retries == 3
    
    def test_timeout_validation(self):
        """Test timeout must be within valid range."""
        with pytest.raises(ValidationError):
            ConnectionConfig(
                endpoint="https://api.example.com",
                timeout=0
            )
        
        with pytest.raises(ValidationError):
            ConnectionConfig(
                endpoint="https://api.example.com",
                timeout=400
            )
    
    def test_retries_validation(self):
        """Test retries must be within valid range."""
        with pytest.raises(ValidationError):
            ConnectionConfig(
                endpoint="https://api.example.com",
                retries=-1
            )
        
        with pytest.raises(ValidationError):
            ConnectionConfig(
                endpoint="https://api.example.com",
                retries=15
            )


class TestApplicationProfileModel:
    """Test ApplicationProfile model validation."""
    
    def test_valid_application_profile(self):
        """Test creating a valid application profile."""
        profile = ApplicationProfile(
            id="app_123",
            customer_id="cust_123",
            name="Test Chatbot",
            type="chatbot",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com"
            )
        )
        assert profile.id == "app_123"
        assert profile.customer_id == "cust_123"
        assert profile.type == "chatbot"
    
    def test_application_type_validation(self):
        """Test application type must be valid."""
        with pytest.raises(ValidationError):
            ApplicationProfile(
                id="app_123",
                customer_id="cust_123",
                name="Test App",
                type="invalid_type",
                connection_config=ConnectionConfig(
                    endpoint="https://api.example.com"
                )
            )


class TestTestCaseModel:
    """Test TestCase model validation."""
    
    def test_valid_test_case(self):
        """Test creating a valid test case."""
        test_case = TestCase(
            id="tc_001",
            input="What is 2+2?",
            expected_output="4"
        )
        assert test_case.id == "tc_001"
        assert test_case.input == "What is 2+2?"
        assert test_case.expected_output == "4"
    
    def test_test_case_input_validation(self):
        """Test test case input cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                id="tc_001",
                input="   "
            )
        assert "input cannot be empty" in str(exc_info.value)


class TestDatasetModel:
    """Test Dataset model validation."""
    
    def test_valid_dataset(self):
        """Test creating a valid dataset."""
        dataset = Dataset(
            id="ds_123",
            customer_id="cust_123",
            name="Test Dataset",
            description="A test dataset",
            test_cases=[
                TestCase(id="tc_001", input="Question 1"),
                TestCase(id="tc_002", input="Question 2")
            ]
        )
        assert dataset.id == "ds_123"
        assert dataset.customer_id == "cust_123"
        assert len(dataset.test_cases) == 2
    
    def test_dataset_unique_test_case_ids(self):
        """Test dataset test case IDs must be unique."""
        with pytest.raises(ValidationError) as exc_info:
            Dataset(
                id="ds_123",
                customer_id="cust_123",
                name="Test Dataset",
                description="Test",
                test_cases=[
                    TestCase(id="tc_001", input="Question 1"),
                    TestCase(id="tc_001", input="Question 2")
                ]
            )
        assert "must be unique" in str(exc_info.value)


class TestResponseModel:
    """Test Response model validation."""
    
    def test_valid_response(self):
        """Test creating a valid response."""
        response = Response(
            test_case_id="tc_001",
            input="What is 2+2?",
            output="4",
            latency=100.5
        )
        assert response.test_case_id == "tc_001"
        assert response.latency == 100.5
    
    def test_response_latency_validation(self):
        """Test response latency cannot be negative."""
        with pytest.raises(ValidationError):
            Response(
                test_case_id="tc_001",
                input="Question",
                output="Answer",
                latency=-10.0
            )


class TestMetricsModels:
    """Test metrics models validation."""
    
    def test_valid_individual_metrics(self):
        """Test creating valid individual metrics."""
        metrics = IndividualMetrics(
            accuracy=0.95,
            relevance=0.88
        )
        assert metrics.accuracy == 0.95
        assert metrics.relevance == 0.88
    
    def test_individual_metrics_range_validation(self):
        """Test individual metrics must be in valid range."""
        with pytest.raises(ValidationError):
            IndividualMetrics(accuracy=1.5)
        
        with pytest.raises(ValidationError):
            IndividualMetrics(relevance=-0.1)
    
    def test_valid_aggregated_metrics(self):
        """Test creating valid aggregated metrics."""
        metrics = AggregatedMetrics(
            average_accuracy=0.92,
            average_relevance=0.87,
            average_latency=245.5,
            median_latency=230.0,
            p95_latency=380.0,
            success_rate=0.98,
            total_test_cases=100,
            failed_test_cases=2
        )
        assert metrics.total_test_cases == 100
        assert metrics.failed_test_cases == 2


class TestEvaluationRunModel:
    """Test EvaluationRun model validation."""
    
    def test_valid_evaluation_run(self):
        """Test creating a valid evaluation run."""
        run = EvaluationRun(
            id="run_123",
            customer_id="cust_123",
            dataset_id="ds_123",
            application_profile_id="app_123",
            status="pending"
        )
        assert run.id == "run_123"
        assert run.status == "pending"
    
    def test_evaluation_run_end_time_validation(self):
        """Test end time must be after start time."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 11, 0, 0)  # Before start
        
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRun(
                id="run_123",
                customer_id="cust_123",
                dataset_id="ds_123",
                application_profile_id="app_123",
                start_time=start,
                end_time=end
            )
        assert "End time cannot be before start time" in str(exc_info.value)
    
    def test_evaluation_run_metrics_consistency(self):
        """Test metrics must be consistent with responses."""
        responses = [
            Response(
                test_case_id="tc_001",
                input="Q1",
                output="A1",
                latency=100.0
            )
        ]
        
        # Metrics with wrong total_test_cases
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRun(
                id="run_123",
                customer_id="cust_123",
                dataset_id="ds_123",
                application_profile_id="app_123",
                responses=responses,
                metrics=AggregatedMetrics(
                    average_accuracy=0.9,
                    average_relevance=0.9,
                    average_latency=100.0,
                    median_latency=100.0,
                    p95_latency=100.0,
                    success_rate=1.0,
                    total_test_cases=5,  # Wrong!
                    failed_test_cases=0
                )
            )
        assert "must match number of responses" in str(exc_info.value)
