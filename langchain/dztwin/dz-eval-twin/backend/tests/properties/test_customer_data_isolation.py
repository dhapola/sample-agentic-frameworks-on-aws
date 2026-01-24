"""Property-based tests for customer data isolation.

Feature: gen-ai-eval-platform
Property: Customer data isolation
Validates: Requirements 0.1, 0.3, 0.4
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List

from app.database.repository import DataRepository
from app.models.customer import Customer
from app.models.dataset import Dataset
from app.models.test_case import TestCase
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.evaluation_run import EvaluationRun


# ==================== Hypothesis Strategies ====================

@st.composite
def customer_id_strategy(draw):
    """Generate valid customer IDs."""
    prefix = draw(st.sampled_from(["cust", "customer", "tenant"]))
    suffix = draw(st.integers(min_value=1000, max_value=9999))
    return f"{prefix}_{suffix}"


@st.composite
def customer_strategy(draw):
    """Generate valid Customer objects."""
    customer_id = draw(customer_id_strategy())
    name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    # Generate simple valid email
    email_local = draw(st.text(min_size=3, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'))
    email_domain = draw(st.text(min_size=3, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'))
    email = f"{email_local}@{email_domain}.com"
    
    return Customer(
        id=customer_id,
        name=name.strip() or "Customer",  # Ensure non-empty
        contact_email=email,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@st.composite
def dataset_strategy(draw, customer_id: str):
    """Generate valid Dataset objects for a specific customer."""
    dataset_id = f"dataset_{draw(st.integers(min_value=1000, max_value=9999))}"
    name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    description = draw(st.text(max_size=200))
    
    # Generate 0-5 test cases
    num_test_cases = draw(st.integers(min_value=0, max_value=5))
    test_cases = []
    for i in range(num_test_cases):
        test_case = TestCase(
            id=f"tc_{dataset_id}_{i}",
            input=draw(st.text(min_size=1, max_size=100)),
            expected_output=draw(st.one_of(st.none(), st.text(max_size=100)))
        )
        test_cases.append(test_case)
    
    return Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name=name.strip() or "Dataset",  # Ensure non-empty
        description=description,
        test_cases=test_cases,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@st.composite
def application_profile_strategy(draw, customer_id: str):
    """Generate valid ApplicationProfile objects for a specific customer."""
    profile_id = f"app_{draw(st.integers(min_value=1000, max_value=9999))}"
    name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    app_type = draw(st.sampled_from(["chatbot", "rag", "agent", "workflow", "custom"]))
    
    connection_config = ConnectionConfig(
        endpoint=f"https://api.example.com/{draw(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'))}",
        timeout=draw(st.integers(min_value=10, max_value=60)),
        retries=draw(st.integers(min_value=1, max_value=5))
    )
    
    return ApplicationProfile(
        id=profile_id,
        customer_id=customer_id,
        name=name.strip() or "Profile",  # Ensure non-empty
        type=app_type,
        connection_config=connection_config,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@st.composite
def evaluation_run_strategy(draw, customer_id: str, dataset_id: str, profile_id: str):
    """Generate valid EvaluationRun objects for a specific customer."""
    run_id = f"run_{draw(st.integers(min_value=1000, max_value=9999))}"
    status = draw(st.sampled_from(["pending", "running", "completed", "failed"]))
    
    return EvaluationRun(
        id=run_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        application_profile_id=profile_id,
        status=status,
        start_time=datetime.utcnow(),
        responses=[]
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    customer1=customer_strategy(),
    customer2=customer_strategy(),
    num_datasets_c1=st.integers(min_value=1, max_value=3),
    num_datasets_c2=st.integers(min_value=1, max_value=3)
)
async def test_dataset_queries_never_return_other_customer_data(
    customer1: Customer,
    customer2: Customer,
    num_datasets_c1: int,
    num_datasets_c2: int
):
    """
    Property: Customer data isolation for datasets.
    
    **Validates: Requirements 0.1, 0.3, 0.4**
    
    For any two distinct customers, querying datasets for customer1
    should never return datasets belonging to customer2.
    """
    # Ensure customers are different
    if customer1.id == customer2.id:
        customer2.id = customer2.id + "_different"
    
    # Create mock database inside the test
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.datasets = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Create datasets for customer1
    datasets_c1 = []
    for i in range(num_datasets_c1):
        dataset = Dataset(
            id=f"dataset_c1_{i}",
            customer_id=customer1.id,
            name=f"Dataset C1 {i}",
            description=f"Dataset for customer 1, number {i}",
            test_cases=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        datasets_c1.append(dataset)
    
    # Create datasets for customer2
    datasets_c2 = []
    for i in range(num_datasets_c2):
        dataset = Dataset(
            id=f"dataset_c2_{i}",
            customer_id=customer2.id,
            name=f"Dataset C2 {i}",
            description=f"Dataset for customer 2, number {i}",
            test_cases=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        datasets_c2.append(dataset)
    
    # Mock the database to return appropriate datasets based on customer_id
    def mock_find_datasets(query):
        """Mock find that filters by customer_id."""
        customer_id = query.get("customerId")
        if customer_id == customer1.id:
            return MockCursor([_dataset_to_doc(d) for d in datasets_c1])
        elif customer_id == customer2.id:
            return MockCursor([_dataset_to_doc(d) for d in datasets_c2])
        else:
            return MockCursor([])
    
    mock_database.datasets.find = mock_find_datasets
    
    # Query datasets for customer1
    result_c1 = await repository.get_datasets(customer1.id)
    
    # Query datasets for customer2
    result_c2 = await repository.get_datasets(customer2.id)
    
    # Property: Customer1's query should only return customer1's datasets
    assert len(result_c1) == num_datasets_c1, \
        f"Expected {num_datasets_c1} datasets for customer1, got {len(result_c1)}"
    
    for dataset in result_c1:
        assert dataset.customer_id == customer1.id, \
            f"Dataset {dataset.id} has customer_id {dataset.customer_id}, expected {customer1.id}"
    
    # Property: Customer2's query should only return customer2's datasets
    assert len(result_c2) == num_datasets_c2, \
        f"Expected {num_datasets_c2} datasets for customer2, got {len(result_c2)}"
    
    for dataset in result_c2:
        assert dataset.customer_id == customer2.id, \
            f"Dataset {dataset.id} has customer_id {dataset.customer_id}, expected {customer2.id}"
    
    # Property: No overlap between customer1 and customer2 datasets
    c1_ids = {d.id for d in result_c1}
    c2_ids = {d.id for d in result_c2}
    assert c1_ids.isdisjoint(c2_ids), \
        f"Customer datasets should not overlap. Overlap: {c1_ids & c2_ids}"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    customer1=customer_strategy(),
    customer2=customer_strategy(),
    num_profiles_c1=st.integers(min_value=1, max_value=3),
    num_profiles_c2=st.integers(min_value=1, max_value=3)
)
async def test_application_profile_queries_never_return_other_customer_data(
    customer1: Customer,
    customer2: Customer,
    num_profiles_c1: int,
    num_profiles_c2: int
):
    """
    Property: Customer data isolation for application profiles.
    
    **Validates: Requirements 0.1, 0.3, 0.4**
    
    For any two distinct customers, querying application profiles for customer1
    should never return profiles belonging to customer2.
    """
    # Ensure customers are different
    if customer1.id == customer2.id:
        customer2.id = customer2.id + "_different"
    
    # Create mock database inside the test
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.applicationProfiles = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Create application profiles for customer1
    profiles_c1 = []
    for i in range(num_profiles_c1):
        profile = ApplicationProfile(
            id=f"app_c1_{i}",
            customer_id=customer1.id,
            name=f"Profile C1 {i}",
            type="chatbot",
            connection_config=ConnectionConfig(
                endpoint=f"https://api.example.com/c1/{i}",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        profiles_c1.append(profile)
    
    # Create application profiles for customer2
    profiles_c2 = []
    for i in range(num_profiles_c2):
        profile = ApplicationProfile(
            id=f"app_c2_{i}",
            customer_id=customer2.id,
            name=f"Profile C2 {i}",
            type="rag",
            connection_config=ConnectionConfig(
                endpoint=f"https://api.example.com/c2/{i}",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        profiles_c2.append(profile)
    
    # Mock the database to return appropriate profiles based on customer_id
    def mock_find_profiles(query):
        """Mock find that filters by customer_id."""
        customer_id = query.get("customerId")
        if customer_id == customer1.id:
            return MockCursor([_profile_to_doc(p) for p in profiles_c1])
        elif customer_id == customer2.id:
            return MockCursor([_profile_to_doc(p) for p in profiles_c2])
        else:
            return MockCursor([])
    
    mock_database.applicationProfiles.find = mock_find_profiles
    
    # Query profiles for customer1
    result_c1 = await repository.get_application_profiles(customer1.id)
    
    # Query profiles for customer2
    result_c2 = await repository.get_application_profiles(customer2.id)
    
    # Property: Customer1's query should only return customer1's profiles
    assert len(result_c1) == num_profiles_c1, \
        f"Expected {num_profiles_c1} profiles for customer1, got {len(result_c1)}"
    
    for profile in result_c1:
        assert profile.customer_id == customer1.id, \
            f"Profile {profile.id} has customer_id {profile.customer_id}, expected {customer1.id}"
    
    # Property: Customer2's query should only return customer2's profiles
    assert len(result_c2) == num_profiles_c2, \
        f"Expected {num_profiles_c2} profiles for customer2, got {len(result_c2)}"
    
    for profile in result_c2:
        assert profile.customer_id == customer2.id, \
            f"Profile {profile.id} has customer_id {profile.customer_id}, expected {customer2.id}"
    
    # Property: No overlap between customer1 and customer2 profiles
    c1_ids = {p.id for p in result_c1}
    c2_ids = {p.id for p in result_c2}
    assert c1_ids.isdisjoint(c2_ids), \
        f"Customer profiles should not overlap. Overlap: {c1_ids & c2_ids}"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    customer1=customer_strategy(),
    customer2=customer_strategy(),
    num_runs_c1=st.integers(min_value=1, max_value=3),
    num_runs_c2=st.integers(min_value=1, max_value=3)
)
async def test_evaluation_run_queries_never_return_other_customer_data(
    customer1: Customer,
    customer2: Customer,
    num_runs_c1: int,
    num_runs_c2: int
):
    """
    Property: Customer data isolation for evaluation runs.
    
    **Validates: Requirements 0.1, 0.3, 0.4**
    
    For any two distinct customers, querying evaluation runs for customer1
    should never return runs belonging to customer2.
    """
    # Ensure customers are different
    if customer1.id == customer2.id:
        customer2.id = customer2.id + "_different"
    
    # Create mock database inside the test
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.evaluationRuns = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Create evaluation runs for customer1
    runs_c1 = []
    for i in range(num_runs_c1):
        run = EvaluationRun(
            id=f"run_c1_{i}",
            customer_id=customer1.id,
            dataset_id=f"dataset_c1_{i}",
            application_profile_id=f"app_c1_{i}",
            status="completed",
            start_time=datetime.utcnow(),
            responses=[]
        )
        runs_c1.append(run)
    
    # Create evaluation runs for customer2
    runs_c2 = []
    for i in range(num_runs_c2):
        run = EvaluationRun(
            id=f"run_c2_{i}",
            customer_id=customer2.id,
            dataset_id=f"dataset_c2_{i}",
            application_profile_id=f"app_c2_{i}",
            status="pending",
            start_time=datetime.utcnow(),
            responses=[]
        )
        runs_c2.append(run)
    
    # Mock the database to return appropriate runs based on customer_id
    def mock_find_runs(query):
        """Mock find that filters by customer_id."""
        customer_id = query.get("customerId")
        if customer_id == customer1.id:
            return MockCursor([_run_to_doc(r) for r in runs_c1])
        elif customer_id == customer2.id:
            return MockCursor([_run_to_doc(r) for r in runs_c2])
        else:
            return MockCursor([])
    
    mock_database.evaluationRuns.find = mock_find_runs
    
    # Query runs for customer1
    result_c1 = await repository.get_evaluation_runs(customer1.id)
    
    # Query runs for customer2
    result_c2 = await repository.get_evaluation_runs(customer2.id)
    
    # Property: Customer1's query should only return customer1's runs
    assert len(result_c1) == num_runs_c1, \
        f"Expected {num_runs_c1} runs for customer1, got {len(result_c1)}"
    
    for run in result_c1:
        assert run.customer_id == customer1.id, \
            f"Run {run.id} has customer_id {run.customer_id}, expected {customer1.id}"
    
    # Property: Customer2's query should only return customer2's runs
    assert len(result_c2) == num_runs_c2, \
        f"Expected {num_runs_c2} runs for customer2, got {len(result_c2)}"
    
    for run in result_c2:
        assert run.customer_id == customer2.id, \
            f"Run {run.id} has customer_id {run.customer_id}, expected {customer2.id}"
    
    # Property: No overlap between customer1 and customer2 runs
    c1_ids = {r.id for r in result_c1}
    c2_ids = {r.id for r in result_c2}
    assert c1_ids.isdisjoint(c2_ids), \
        f"Customer runs should not overlap. Overlap: {c1_ids & c2_ids}"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    customer1=customer_strategy(),
    customer2=customer_strategy()
)
async def test_get_dataset_by_id_enforces_tenant_isolation(
    customer1: Customer,
    customer2: Customer
):
    """
    Property: Get dataset by ID enforces tenant isolation.
    
    **Validates: Requirements 0.1, 0.3, 0.4**
    
    For any dataset belonging to customer1, attempting to retrieve it
    with customer2's ID should return None (access denied).
    """
    # Ensure customers are different
    if customer1.id == customer2.id:
        customer2.id = customer2.id + "_different"
    
    # Create mock database inside the test
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.datasets = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Create a dataset for customer1
    dataset_c1 = Dataset(
        id="dataset_test",
        customer_id=customer1.id,
        name="Test Dataset",
        description="Test",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Mock the database find_one to enforce tenant check
    async def mock_find_one_dataset(query):
        """Mock find_one that enforces customer_id check."""
        if query.get("_id") == dataset_c1.id and query.get("customerId") == customer1.id:
            return _dataset_to_doc(dataset_c1)
        return None
    
    mock_database.datasets.find_one = mock_find_one_dataset
    
    # Property: Customer1 can retrieve their own dataset
    result_c1 = await repository.get_dataset_by_id(dataset_c1.id, customer1.id)
    assert result_c1 is not None, "Customer1 should be able to retrieve their own dataset"
    assert result_c1.customer_id == customer1.id
    
    # Property: Customer2 cannot retrieve customer1's dataset
    result_c2 = await repository.get_dataset_by_id(dataset_c1.id, customer2.id)
    assert result_c2 is None, \
        "Customer2 should NOT be able to retrieve customer1's dataset"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    customer1=customer_strategy(),
    customer2=customer_strategy()
)
async def test_get_evaluation_run_by_id_enforces_tenant_isolation(
    customer1: Customer,
    customer2: Customer
):
    """
    Property: Get evaluation run by ID enforces tenant isolation.
    
    **Validates: Requirements 0.1, 0.3, 0.4**
    
    For any evaluation run belonging to customer1, attempting to retrieve it
    with customer2's ID should return None (access denied).
    """
    # Ensure customers are different
    if customer1.id == customer2.id:
        customer2.id = customer2.id + "_different"
    
    # Create mock database inside the test
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.evaluationRuns = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Create an evaluation run for customer1
    run_c1 = EvaluationRun(
        id="run_test",
        customer_id=customer1.id,
        dataset_id="dataset_test",
        application_profile_id="app_test",
        status="completed",
        start_time=datetime.utcnow(),
        responses=[]
    )
    
    # Mock the database find_one to enforce tenant check
    async def mock_find_one_run(query):
        """Mock find_one that enforces customer_id check."""
        if query.get("_id") == run_c1.id and query.get("customerId") == customer1.id:
            return _run_to_doc(run_c1)
        return None
    
    mock_database.evaluationRuns.find_one = mock_find_one_run
    
    # Property: Customer1 can retrieve their own run
    result_c1 = await repository.get_evaluation_run_by_id(run_c1.id, customer1.id)
    assert result_c1 is not None, "Customer1 should be able to retrieve their own run"
    assert result_c1.customer_id == customer1.id
    
    # Property: Customer2 cannot retrieve customer1's run
    result_c2 = await repository.get_evaluation_run_by_id(run_c1.id, customer2.id)
    assert result_c2 is None, \
        "Customer2 should NOT be able to retrieve customer1's run"


# ==================== Helper Functions ====================

def _dataset_to_doc(dataset: Dataset) -> dict:
    """Convert Dataset to MongoDB document format."""
    doc = dataset.model_dump()
    doc["_id"] = doc.pop("id")
    doc["customerId"] = doc.pop("customer_id")
    doc["testCases"] = doc.pop("test_cases")
    return doc


def _profile_to_doc(profile: ApplicationProfile) -> dict:
    """Convert ApplicationProfile to MongoDB document format."""
    doc = profile.model_dump()
    doc["_id"] = doc.pop("id")
    doc["customerId"] = doc.pop("customer_id")
    doc["connectionConfig"] = doc.pop("connection_config")
    return doc


def _run_to_doc(run: EvaluationRun) -> dict:
    """Convert EvaluationRun to MongoDB document format."""
    doc = run.model_dump()
    doc["_id"] = doc.pop("id")
    doc["customerId"] = doc.pop("customer_id")
    doc["datasetId"] = doc.pop("dataset_id")
    doc["applicationProfileId"] = doc.pop("application_profile_id")
    doc["startTime"] = doc.pop("start_time")
    if "end_time" in doc:
        doc["endTime"] = doc.pop("end_time")
    return doc


class MockCursor:
    """Mock async cursor for MongoDB queries."""
    
    def __init__(self, documents: List[dict]):
        self.documents = documents
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        doc = self.documents[self.index]
        self.index += 1
        return doc

