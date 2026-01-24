"""Unit tests for DataRepository with tenant isolation."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.database.repository import DataRepository
from app.models.customer import Customer
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.dataset import Dataset
from app.models.test_case import TestCase
from app.models.evaluation_run import EvaluationRun
from app.models.response import Response


@pytest.fixture
def mock_database():
    """Create a mock MongoDB database."""
    db = MagicMock()
    db.customers = MagicMock()
    db.applicationProfiles = MagicMock()
    db.datasets = MagicMock()
    db.evaluationRuns = MagicMock()
    return db


@pytest.fixture
def repository(mock_database):
    """Create a DataRepository with mock database."""
    return DataRepository(mock_database)


@pytest.fixture
def sample_customer():
    """Create a sample customer."""
    return Customer(
        id="cust_123",
        name="Test Customer",
        contact_email="test@example.com",
        contact_phone="+1-555-0100"
    )


@pytest.fixture
def sample_application_profile():
    """Create a sample application profile."""
    return ApplicationProfile(
        id="app_123",
        customer_id="cust_123",
        name="Test App",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com",
            timeout=30,
            retries=3
        )
    )


@pytest.fixture
def sample_dataset():
    """Create a sample dataset."""
    return Dataset(
        id="dataset_123",
        customer_id="cust_123",
        name="Test Dataset",
        description="Test description",
        test_cases=[
            TestCase(
                id="tc_001",
                input="Test input",
                expected_output="Test output"
            )
        ]
    )


@pytest.fixture
def sample_evaluation_run():
    """Create a sample evaluation run."""
    return EvaluationRun(
        id="run_123",
        customer_id="cust_123",
        dataset_id="dataset_123",
        application_profile_id="app_123",
        status="pending",
        start_time=datetime.utcnow()
    )


# ==================== Customer Tests ====================

@pytest.mark.asyncio
async def test_create_customer_success(repository, mock_database, sample_customer):
    """Test successful customer creation."""
    mock_database.customers.insert_one = AsyncMock(return_value=MagicMock(inserted_id="cust_123"))
    
    result = await repository.create_customer(sample_customer)
    
    assert result.id == sample_customer.id
    assert result.name == sample_customer.name
    mock_database.customers.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_create_customer_duplicate(repository, mock_database, sample_customer):
    """Test customer creation with duplicate ID."""
    mock_database.customers.insert_one = AsyncMock(side_effect=DuplicateKeyError("Duplicate"))
    
    with pytest.raises(ValueError, match="already exists"):
        await repository.create_customer(sample_customer)


@pytest.mark.asyncio
async def test_create_customer_database_error(repository, mock_database, sample_customer):
    """Test customer creation with database error."""
    mock_database.customers.insert_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.create_customer(sample_customer)


@pytest.mark.asyncio
async def test_get_customers_success(repository, mock_database):
    """Test successful retrieval of all customers."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "cust_123",
            "name": "Customer 1",
            "contact_email": "test1@example.com",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "cust_456",
            "name": "Customer 2",
            "contact_email": "test2@example.com",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    mock_database.customers.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_customers()
    
    assert len(result) == 2
    assert result[0].id == "cust_123"
    assert result[1].id == "cust_456"


@pytest.mark.asyncio
async def test_get_customer_by_id_found(repository, mock_database):
    """Test getting customer by ID when found."""
    mock_database.customers.find_one = AsyncMock(return_value={
        "_id": "cust_123",
        "name": "Test Customer",
        "contact_email": "test@example.com",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    result = await repository.get_customer_by_id("cust_123")
    
    assert result is not None
    assert result.id == "cust_123"
    assert result.name == "Test Customer"


@pytest.mark.asyncio
async def test_get_customer_by_id_not_found(repository, mock_database):
    """Test getting customer by ID when not found."""
    mock_database.customers.find_one = AsyncMock(return_value=None)
    
    result = await repository.get_customer_by_id("nonexistent")
    
    assert result is None


@pytest.mark.asyncio
async def test_update_customer_success(repository, mock_database):
    """Test successful customer update."""
    mock_database.customers.find_one_and_update = AsyncMock(return_value={
        "_id": "cust_123",
        "name": "Updated Customer",
        "contact_email": "updated@example.com",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    result = await repository.update_customer("cust_123", {"name": "Updated Customer"})
    
    assert result.name == "Updated Customer"


@pytest.mark.asyncio
async def test_update_customer_not_found(repository, mock_database):
    """Test updating non-existent customer."""
    mock_database.customers.find_one_and_update = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="not found"):
        await repository.update_customer("nonexistent", {"name": "Updated"})


@pytest.mark.asyncio
async def test_delete_customer_success(repository, mock_database):
    """Test successful customer deletion."""
    mock_database.customers.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    
    await repository.delete_customer("cust_123")
    
    mock_database.customers.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_customer_not_found(repository, mock_database):
    """Test deleting non-existent customer."""
    mock_database.customers.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    
    with pytest.raises(ValueError, match="not found"):
        await repository.delete_customer("nonexistent")


# ==================== Application Profile Tests ====================

@pytest.mark.asyncio
async def test_create_application_profile_success(repository, mock_database, sample_application_profile):
    """Test successful application profile creation."""
    mock_database.applicationProfiles.insert_one = AsyncMock(return_value=MagicMock(inserted_id="app_123"))
    
    result = await repository.create_application_profile(sample_application_profile)
    
    assert result.id == sample_application_profile.id
    assert result.customer_id == sample_application_profile.customer_id
    mock_database.applicationProfiles.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_application_profiles_all(repository, mock_database):
    """Test getting all application profiles."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "app_123",
            "customerId": "cust_123",
            "name": "App 1",
            "type": "chatbot",
            "connectionConfig": {"endpoint": "https://api.example.com", "timeout": 30, "retries": 3},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    mock_database.applicationProfiles.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_application_profiles()
    
    assert len(result) == 1
    assert result[0].id == "app_123"


@pytest.mark.asyncio
async def test_get_application_profiles_filtered_by_customer(repository, mock_database):
    """Test getting application profiles filtered by customer."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "app_123",
            "customerId": "cust_123",
            "name": "App 1",
            "type": "chatbot",
            "connectionConfig": {"endpoint": "https://api.example.com", "timeout": 30, "retries": 3},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    mock_database.applicationProfiles.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_application_profiles(customer_id="cust_123")
    
    assert len(result) == 1
    assert result[0].customer_id == "cust_123"
    # Verify the query included customer_id filter
    call_args = mock_database.applicationProfiles.find.call_args[0][0]
    assert call_args["customerId"] == "cust_123"


# ==================== Dataset Tests (Tenant-Scoped) ====================

@pytest.mark.asyncio
async def test_create_dataset_success(repository, mock_database, sample_dataset):
    """Test successful dataset creation."""
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_123"))
    
    result = await repository.create_dataset(sample_dataset)
    
    assert result.id == sample_dataset.id
    assert result.customer_id == sample_dataset.customer_id
    mock_database.datasets.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_datasets_tenant_scoped(repository, mock_database):
    """Test getting datasets is tenant-scoped."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "dataset_123",
            "customerId": "cust_123",
            "name": "Dataset 1",
            "description": "Test",
            "testCases": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    mock_database.datasets.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_datasets("cust_123")
    
    assert len(result) == 1
    assert result[0].customer_id == "cust_123"
    # Verify the query included customer_id filter
    call_args = mock_database.datasets.find.call_args[0][0]
    assert call_args["customerId"] == "cust_123"


@pytest.mark.asyncio
async def test_get_dataset_by_id_tenant_check(repository, mock_database):
    """Test getting dataset by ID enforces tenant check."""
    mock_database.datasets.find_one = AsyncMock(return_value={
        "_id": "dataset_123",
        "customerId": "cust_123",
        "name": "Dataset 1",
        "description": "Test",
        "testCases": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    result = await repository.get_dataset_by_id("dataset_123", "cust_123")
    
    assert result is not None
    assert result.customer_id == "cust_123"
    # Verify the query included both id and customer_id
    call_args = mock_database.datasets.find_one.call_args[0][0]
    assert call_args["_id"] == "dataset_123"
    assert call_args["customerId"] == "cust_123"


@pytest.mark.asyncio
async def test_get_dataset_by_id_wrong_customer(repository, mock_database):
    """Test getting dataset with wrong customer returns None."""
    mock_database.datasets.find_one = AsyncMock(return_value=None)
    
    result = await repository.get_dataset_by_id("dataset_123", "wrong_customer")
    
    assert result is None


@pytest.mark.asyncio
async def test_update_dataset_tenant_check(repository, mock_database):
    """Test updating dataset enforces tenant check."""
    mock_database.datasets.find_one_and_update = AsyncMock(return_value={
        "_id": "dataset_123",
        "customerId": "cust_123",
        "name": "Updated Dataset",
        "description": "Test",
        "testCases": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    result = await repository.update_dataset("dataset_123", "cust_123", {"name": "Updated Dataset"})
    
    assert result.name == "Updated Dataset"
    # Verify the query included both id and customer_id
    call_args = mock_database.datasets.find_one_and_update.call_args[0][0]
    assert call_args["_id"] == "dataset_123"
    assert call_args["customerId"] == "cust_123"


@pytest.mark.asyncio
async def test_delete_dataset_tenant_check(repository, mock_database):
    """Test deleting dataset enforces tenant check."""
    mock_database.datasets.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    
    await repository.delete_dataset("dataset_123", "cust_123")
    
    # Verify the query included both id and customer_id
    call_args = mock_database.datasets.delete_one.call_args[0][0]
    assert call_args["_id"] == "dataset_123"
    assert call_args["customerId"] == "cust_123"


# ==================== Evaluation Run Tests (Tenant-Scoped) ====================

@pytest.mark.asyncio
async def test_create_evaluation_run_success(repository, mock_database, sample_evaluation_run):
    """Test successful evaluation run creation."""
    mock_database.evaluationRuns.insert_one = AsyncMock(return_value=MagicMock(inserted_id="run_123"))
    
    result = await repository.create_evaluation_run(sample_evaluation_run)
    
    assert result.id == sample_evaluation_run.id
    assert result.customer_id == sample_evaluation_run.customer_id
    mock_database.evaluationRuns.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_evaluation_runs_tenant_scoped(repository, mock_database):
    """Test getting evaluation runs is tenant-scoped."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "run_123",
            "customerId": "cust_123",
            "datasetId": "dataset_123",
            "applicationProfileId": "app_123",
            "status": "completed",
            "startTime": datetime.utcnow(),
            "responses": []
        }
    ]
    mock_database.evaluationRuns.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_evaluation_runs("cust_123")
    
    assert len(result) == 1
    assert result[0].customer_id == "cust_123"
    # Verify the query included customer_id filter
    call_args = mock_database.evaluationRuns.find.call_args[0][0]
    assert call_args["customerId"] == "cust_123"


@pytest.mark.asyncio
async def test_get_evaluation_run_by_id_tenant_check(repository, mock_database):
    """Test getting evaluation run by ID enforces tenant check."""
    mock_database.evaluationRuns.find_one = AsyncMock(return_value={
        "_id": "run_123",
        "customerId": "cust_123",
        "datasetId": "dataset_123",
        "applicationProfileId": "app_123",
        "status": "completed",
        "startTime": datetime.utcnow(),
        "responses": []
    })
    
    result = await repository.get_evaluation_run_by_id("run_123", "cust_123")
    
    assert result is not None
    assert result.customer_id == "cust_123"
    # Verify the query included both id and customer_id
    call_args = mock_database.evaluationRuns.find_one.call_args[0][0]
    assert call_args["_id"] == "run_123"
    assert call_args["customerId"] == "cust_123"


# ==================== Response Tests ====================

@pytest.mark.asyncio
async def test_add_response_success(repository, mock_database):
    """Test adding response to evaluation run."""
    response = Response(
        test_case_id="tc_001",
        input="Test input",
        output="Test output",
        latency=1.5,
        timestamp=datetime.utcnow()
    )
    mock_database.evaluationRuns.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    
    await repository.add_response("run_123", response)
    
    mock_database.evaluationRuns.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_add_response_run_not_found(repository, mock_database):
    """Test adding response to non-existent run."""
    response = Response(
        test_case_id="tc_001",
        input="Test input",
        output="Test output",
        latency=1.5,
        timestamp=datetime.utcnow()
    )
    mock_database.evaluationRuns.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    
    with pytest.raises(ValueError, match="not found"):
        await repository.add_response("nonexistent", response)


@pytest.mark.asyncio
async def test_get_responses_success(repository, mock_database):
    """Test getting responses for evaluation run."""
    mock_database.evaluationRuns.find_one = AsyncMock(return_value={
        "_id": "run_123",
        "responses": [
            {
                "testCaseId": "tc_001",
                "input": "Test input",
                "output": "Test output",
                "latency": 1.5,
                "timestamp": datetime.utcnow()
            }
        ]
    })
    
    result = await repository.get_responses("run_123")
    
    assert len(result) == 1
    assert result[0].test_case_id == "tc_001"


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_empty_dataset_list(repository, mock_database):
    """Test getting datasets when none exist."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = []
    mock_database.datasets.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_datasets("cust_123")
    
    assert len(result) == 0


@pytest.mark.asyncio
async def test_dataset_with_no_test_cases(repository, mock_database):
    """Test creating dataset with empty test cases list."""
    dataset = Dataset(
        id="dataset_empty",
        customer_id="cust_123",
        name="Empty Dataset",
        description="No test cases",
        test_cases=[]
    )
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_empty"))
    
    result = await repository.create_dataset(dataset)
    
    assert result.id == "dataset_empty"
    assert len(result.test_cases) == 0


@pytest.mark.asyncio
async def test_dataset_with_large_test_cases_array(repository, mock_database):
    """Test creating dataset with many test cases."""
    test_cases = [
        TestCase(id=f"tc_{i:03d}", input=f"Input {i}", expected_output=f"Output {i}")
        for i in range(100)
    ]
    dataset = Dataset(
        id="dataset_large",
        customer_id="cust_123",
        name="Large Dataset",
        description="Many test cases",
        test_cases=test_cases
    )
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_large"))
    
    result = await repository.create_dataset(dataset)
    
    assert result.id == "dataset_large"
    assert len(result.test_cases) == 100


# ==================== Additional Edge Cases and Error Conditions ====================

@pytest.mark.asyncio
async def test_dataset_with_very_large_test_cases_array(repository, mock_database):
    """Test creating dataset with 1000+ test cases."""
    test_cases = [
        TestCase(id=f"tc_{i:04d}", input=f"Input {i}", expected_output=f"Output {i}")
        for i in range(1000)
    ]
    dataset = Dataset(
        id="dataset_very_large",
        customer_id="cust_123",
        name="Very Large Dataset",
        description="1000 test cases",
        test_cases=test_cases
    )
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_very_large"))
    
    result = await repository.create_dataset(dataset)
    
    assert result.id == "dataset_very_large"
    assert len(result.test_cases) == 1000


@pytest.mark.asyncio
async def test_dataset_with_test_cases_no_expected_output(repository, mock_database):
    """Test creating dataset with test cases that have no expected output."""
    test_cases = [
        TestCase(id="tc_001", input="Input without expected output", expected_output=None),
        TestCase(id="tc_002", input="Another input", expected_output=None)
    ]
    dataset = Dataset(
        id="dataset_no_expected",
        customer_id="cust_123",
        name="Dataset Without Expected Outputs",
        description="Test cases without expected outputs",
        test_cases=test_cases
    )
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_no_expected"))
    
    result = await repository.create_dataset(dataset)
    
    assert result.id == "dataset_no_expected"
    assert all(tc.expected_output is None for tc in result.test_cases)


@pytest.mark.asyncio
async def test_application_profile_database_error(repository, mock_database, sample_application_profile):
    """Test application profile creation with database error."""
    mock_database.applicationProfiles.insert_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.create_application_profile(sample_application_profile)


@pytest.mark.asyncio
async def test_dataset_database_error(repository, mock_database, sample_dataset):
    """Test dataset creation with database error."""
    mock_database.datasets.insert_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.create_dataset(sample_dataset)


@pytest.mark.asyncio
async def test_evaluation_run_database_error(repository, mock_database, sample_evaluation_run):
    """Test evaluation run creation with database error."""
    mock_database.evaluationRuns.insert_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.create_evaluation_run(sample_evaluation_run)


@pytest.mark.asyncio
async def test_get_datasets_database_error(repository, mock_database):
    """Test getting datasets with database error."""
    mock_database.datasets.find = MagicMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.get_datasets("cust_123")


@pytest.mark.asyncio
async def test_get_application_profiles_database_error(repository, mock_database):
    """Test getting application profiles with database error."""
    mock_database.applicationProfiles.find = MagicMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.get_application_profiles()


@pytest.mark.asyncio
async def test_get_evaluation_runs_database_error(repository, mock_database):
    """Test getting evaluation runs with database error."""
    mock_database.evaluationRuns.find = MagicMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.get_evaluation_runs("cust_123")


@pytest.mark.asyncio
async def test_update_dataset_database_error(repository, mock_database):
    """Test updating dataset with database error."""
    mock_database.datasets.find_one_and_update = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.update_dataset("dataset_123", "cust_123", {"name": "Updated"})


@pytest.mark.asyncio
async def test_delete_dataset_database_error(repository, mock_database):
    """Test deleting dataset with database error."""
    mock_database.datasets.delete_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.delete_dataset("dataset_123", "cust_123")


@pytest.mark.asyncio
async def test_update_evaluation_run_tenant_check(repository, mock_database):
    """Test updating evaluation run enforces tenant check."""
    mock_database.evaluationRuns.find_one_and_update = AsyncMock(return_value={
        "_id": "run_123",
        "customerId": "cust_123",
        "datasetId": "dataset_123",
        "applicationProfileId": "app_123",
        "status": "completed",
        "startTime": datetime.utcnow(),
        "responses": []
    })
    
    result = await repository.update_evaluation_run("run_123", "cust_123", {"status": "completed"})
    
    assert result.status == "completed"
    # Verify the query included both id and customer_id
    call_args = mock_database.evaluationRuns.find_one_and_update.call_args[0][0]
    assert call_args["_id"] == "run_123"
    assert call_args["customerId"] == "cust_123"


@pytest.mark.asyncio
async def test_update_evaluation_run_wrong_customer(repository, mock_database):
    """Test updating evaluation run with wrong customer fails."""
    mock_database.evaluationRuns.find_one_and_update = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="not found"):
        await repository.update_evaluation_run("run_123", "wrong_customer", {"status": "completed"})


@pytest.mark.asyncio
async def test_update_application_profile_tenant_isolation(repository, mock_database):
    """Test updating application profile (no tenant check but should work)."""
    mock_database.applicationProfiles.find_one_and_update = AsyncMock(return_value={
        "_id": "app_123",
        "customerId": "cust_123",
        "name": "Updated App",
        "type": "chatbot",
        "connectionConfig": {"endpoint": "https://api.example.com", "timeout": 30, "retries": 3},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    result = await repository.update_application_profile("app_123", {"name": "Updated App"})
    
    assert result.name == "Updated App"


@pytest.mark.asyncio
async def test_delete_application_profile_success(repository, mock_database):
    """Test deleting application profile."""
    mock_database.applicationProfiles.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    
    await repository.delete_application_profile("app_123")
    
    mock_database.applicationProfiles.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_application_profile_not_found(repository, mock_database):
    """Test deleting non-existent application profile."""
    mock_database.applicationProfiles.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    
    with pytest.raises(ValueError, match="not found"):
        await repository.delete_application_profile("nonexistent")


@pytest.mark.asyncio
async def test_get_responses_run_not_found(repository, mock_database):
    """Test getting responses for non-existent run."""
    mock_database.evaluationRuns.find_one = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="not found"):
        await repository.get_responses("nonexistent")


@pytest.mark.asyncio
async def test_get_responses_empty_list(repository, mock_database):
    """Test getting responses when run has no responses."""
    mock_database.evaluationRuns.find_one = AsyncMock(return_value={
        "_id": "run_123",
        "responses": []
    })
    
    result = await repository.get_responses("run_123")
    
    assert len(result) == 0


@pytest.mark.asyncio
async def test_add_response_database_error(repository, mock_database):
    """Test adding response with database error."""
    response = Response(
        test_case_id="tc_001",
        input="Test input",
        output="Test output",
        latency=1.5,
        timestamp=datetime.utcnow()
    )
    mock_database.evaluationRuns.update_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.add_response("run_123", response)


@pytest.mark.asyncio
async def test_get_responses_database_error(repository, mock_database):
    """Test getting responses with database error."""
    mock_database.evaluationRuns.find_one = AsyncMock(side_effect=PyMongoError("DB Error"))
    
    with pytest.raises(RuntimeError, match="Database error"):
        await repository.get_responses("run_123")


@pytest.mark.asyncio
async def test_tenant_isolation_multiple_customers_datasets(repository, mock_database):
    """Test that datasets for different customers are properly isolated."""
    # Create datasets for two different customers
    dataset1 = Dataset(
        id="dataset_c1",
        customer_id="cust_123",
        name="Customer 1 Dataset",
        description="Test",
        test_cases=[]
    )
    dataset2 = Dataset(
        id="dataset_c2",
        customer_id="cust_456",
        name="Customer 2 Dataset",
        description="Test",
        test_cases=[]
    )
    
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_c1"))
    await repository.create_dataset(dataset1)
    
    mock_database.datasets.insert_one = AsyncMock(return_value=MagicMock(inserted_id="dataset_c2"))
    await repository.create_dataset(dataset2)
    
    # Mock getting datasets for customer 1
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "dataset_c1",
            "customerId": "cust_123",
            "name": "Customer 1 Dataset",
            "description": "Test",
            "testCases": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    mock_database.datasets.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_datasets("cust_123")
    
    # Verify only customer 1's dataset is returned
    assert len(result) == 1
    assert result[0].customer_id == "cust_123"
    assert result[0].id == "dataset_c1"


@pytest.mark.asyncio
async def test_tenant_isolation_multiple_customers_evaluation_runs(repository, mock_database):
    """Test that evaluation runs for different customers are properly isolated."""
    # Mock getting evaluation runs for customer 1
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = [
        {
            "_id": "run_c1",
            "customerId": "cust_123",
            "datasetId": "dataset_c1",
            "applicationProfileId": "app_c1",
            "status": "completed",
            "startTime": datetime.utcnow(),
            "responses": []
        }
    ]
    mock_database.evaluationRuns.find = MagicMock(return_value=mock_cursor)
    
    result = await repository.get_evaluation_runs("cust_123")
    
    # Verify only customer 1's runs are returned
    assert len(result) == 1
    assert result[0].customer_id == "cust_123"
    assert result[0].id == "run_c1"
    
    # Verify the query enforced customer_id filter
    call_args = mock_database.evaluationRuns.find.call_args[0][0]
    assert call_args["customerId"] == "cust_123"
