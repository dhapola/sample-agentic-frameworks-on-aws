"""Property-based tests for list operations with tenant isolation.

Feature: gen-ai-eval-platform
Properties: List operations return all entities with proper tenant isolation
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.test_case import TestCase


# ==================== Hypothesis Strategies ====================

@st.composite
def testcase_strategy(draw, dataset_id: str):
    """Generate valid TestCase objects with unique IDs."""
    tc_num = draw(st.integers(min_value=0, max_value=999))
    tc_id = f"{dataset_id}_tc_{tc_num}"
    input_text = draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    # Optional expected output
    expected_output = draw(st.one_of(
        st.none(),
        st.text(max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
        ))
    ))
    
    return TestCase(
        id=tc_id,
        input=input_text.strip() or "test input",  # Ensure non-empty
        expected_output=expected_output.strip() if expected_output else None
    )


@st.composite
def dataset_strategy(draw, customer_id: str):
    """Generate valid Dataset objects for a specific customer."""
    dataset_num = draw(st.integers(min_value=1000, max_value=9999))
    dataset_id = f"dataset_{customer_id}_{dataset_num}"
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    description = draw(st.text(max_size=500, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    
    # Generate 0-5 test cases
    num_test_cases = draw(st.integers(min_value=0, max_value=5))
    test_cases = []
    for i in range(num_test_cases):
        test_case = draw(testcase_strategy(dataset_id))
        # Ensure unique IDs within dataset
        test_case.id = f"{dataset_id}_tc_{i}"
        test_cases.append(test_case)
    
    return Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name=name.strip() or "Test Dataset",  # Ensure non-empty
        description=description.strip(),
        test_cases=test_cases,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@st.composite
def evaluation_run_strategy(draw, customer_id: str, dataset_id: str):
    """Generate valid EvaluationRun objects for a specific customer."""
    run_num = draw(st.integers(min_value=1000, max_value=9999))
    run_id = f"run_{customer_id}_{run_num}"
    profile_id = f"profile_{customer_id}_001"
    status = draw(st.sampled_from(["pending", "running", "completed", "failed"]))
    
    return EvaluationRun(
        id=run_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        application_profile_id=profile_id,
        status=status,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() if status in ["completed", "failed"] else None,
        responses=[],
        metrics=None
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    num_datasets_customer1=st.integers(min_value=1, max_value=5),
    num_datasets_customer2=st.integers(min_value=1, max_value=5),
    data=st.data()
)
async def test_list_datasets_returns_all_customer_entities(
    num_datasets_customer1: int,
    num_datasets_customer2: int,
    data
):
    """
    Property 4: List operations return all entities.
    
    **Validates: Requirements 1.6, 1.7**
    
    For any collection of created datasets for a customer, listing those datasets
    should return all of them with correct metadata and no datasets from other customers.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer1_id = f"cust_test_{test_run_id}_1"
    customer2_id = f"cust_test_{test_run_id}_2"
    
    # Generate datasets for customer 1
    customer1_datasets = []
    for i in range(num_datasets_customer1):
        dataset = data.draw(dataset_strategy(customer1_id))
        # Ensure unique dataset ID
        dataset.id = f"dataset_{customer1_id}_{test_run_id}_{i}"
        customer1_datasets.append(dataset)
    
    # Generate datasets for customer 2
    customer2_datasets = []
    for i in range(num_datasets_customer2):
        dataset = data.draw(dataset_strategy(customer2_id))
        # Ensure unique dataset ID
        dataset.id = f"dataset_{customer2_id}_{test_run_id}_{i}"
        customer2_datasets.append(dataset)
    
    try:
        # Create all datasets in database
        for dataset in customer1_datasets:
            await repository.create_dataset(dataset)
        
        for dataset in customer2_datasets:
            await repository.create_dataset(dataset)
        
        # List datasets for customer 1
        retrieved_customer1 = await repository.get_datasets(customer1_id)
        
        # List datasets for customer 2
        retrieved_customer2 = await repository.get_datasets(customer2_id)
        
        # Property: Customer 1 should get exactly the number of datasets they created
        assert len(retrieved_customer1) == num_datasets_customer1, \
            f"Customer 1 should have {num_datasets_customer1} datasets, got {len(retrieved_customer1)}"
        
        # Property: Customer 2 should get exactly the number of datasets they created
        assert len(retrieved_customer2) == num_datasets_customer2, \
            f"Customer 2 should have {num_datasets_customer2} datasets, got {len(retrieved_customer2)}"
        
        # Property: All customer 1 dataset IDs should be in the retrieved list
        customer1_ids = {ds.id for ds in customer1_datasets}
        retrieved_customer1_ids = {ds.id for ds in retrieved_customer1}
        
        assert customer1_ids == retrieved_customer1_ids, \
            f"Customer 1 dataset IDs mismatch. Expected: {customer1_ids}, Got: {retrieved_customer1_ids}"
        
        # Property: All customer 2 dataset IDs should be in the retrieved list
        customer2_ids = {ds.id for ds in customer2_datasets}
        retrieved_customer2_ids = {ds.id for ds in retrieved_customer2}
        
        assert customer2_ids == retrieved_customer2_ids, \
            f"Customer 2 dataset IDs mismatch. Expected: {customer2_ids}, Got: {retrieved_customer2_ids}"
        
        # Property: Customer 1 should not see any of customer 2's datasets
        assert customer1_ids.isdisjoint(retrieved_customer2_ids), \
            f"Customer 1 datasets leaked into customer 2's list: {customer1_ids & retrieved_customer2_ids}"
        
        # Property: Customer 2 should not see any of customer 1's datasets
        assert customer2_ids.isdisjoint(retrieved_customer1_ids), \
            f"Customer 2 datasets leaked into customer 1's list: {customer2_ids & retrieved_customer1_ids}"
        
        # Property: All retrieved datasets should have correct customer_id
        for dataset in retrieved_customer1:
            assert dataset.customer_id == customer1_id, \
                f"Dataset {dataset.id} has wrong customer_id: {dataset.customer_id}, expected {customer1_id}"
        
        for dataset in retrieved_customer2:
            assert dataset.customer_id == customer2_id, \
                f"Dataset {dataset.id} has wrong customer_id: {dataset.customer_id}, expected {customer2_id}"
        
        # Property: Retrieved datasets should have all metadata intact
        for original, retrieved in zip(customer1_datasets, retrieved_customer1):
            assert retrieved.name == original.name, \
                f"Dataset {retrieved.id} name mismatch"
            assert retrieved.description == original.description, \
                f"Dataset {retrieved.id} description mismatch"
            assert len(retrieved.test_cases) == len(original.test_cases), \
                f"Dataset {retrieved.id} test case count mismatch"
        
        for original, retrieved in zip(customer2_datasets, retrieved_customer2):
            assert retrieved.name == original.name, \
                f"Dataset {retrieved.id} name mismatch"
            assert retrieved.description == original.description, \
                f"Dataset {retrieved.id} description mismatch"
            assert len(retrieved.test_cases) == len(original.test_cases), \
                f"Dataset {retrieved.id} test case count mismatch"
    
    finally:
        # Cleanup: Delete all test datasets
        for dataset in customer1_datasets:
            try:
                await repository.delete_dataset(dataset.id, customer1_id)
            except Exception:
                pass  # Ignore cleanup errors
        
        for dataset in customer2_datasets:
            try:
                await repository.delete_dataset(dataset.id, customer2_id)
            except Exception:
                pass  # Ignore cleanup errors


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    num_runs_customer1=st.integers(min_value=1, max_value=5),
    num_runs_customer2=st.integers(min_value=1, max_value=5),
    data=st.data()
)
async def test_list_evaluation_runs_returns_all_customer_entities(
    num_runs_customer1: int,
    num_runs_customer2: int,
    data
):
    """
    Property 4: List operations return all entities (evaluation runs).
    
    **Validates: Requirements 1.6, 1.7**
    
    For any collection of created evaluation runs for a customer, listing those runs
    should return all of them with correct metadata and no runs from other customers.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer1_id = f"cust_test_{test_run_id}_1"
    customer2_id = f"cust_test_{test_run_id}_2"
    
    # Create datasets for both customers (needed for evaluation runs)
    dataset1_id = f"dataset_{customer1_id}_{test_run_id}"
    dataset1 = Dataset(
        id=dataset1_id,
        customer_id=customer1_id,
        name="Test Dataset 1",
        description="Test dataset for customer 1",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    dataset2_id = f"dataset_{customer2_id}_{test_run_id}"
    dataset2 = Dataset(
        id=dataset2_id,
        customer_id=customer2_id,
        name="Test Dataset 2",
        description="Test dataset for customer 2",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Generate evaluation runs for customer 1
    customer1_runs = []
    for i in range(num_runs_customer1):
        run = data.draw(evaluation_run_strategy(customer1_id, dataset1_id))
        # Ensure unique run ID
        run.id = f"run_{customer1_id}_{test_run_id}_{i}"
        customer1_runs.append(run)
    
    # Generate evaluation runs for customer 2
    customer2_runs = []
    for i in range(num_runs_customer2):
        run = data.draw(evaluation_run_strategy(customer2_id, dataset2_id))
        # Ensure unique run ID
        run.id = f"run_{customer2_id}_{test_run_id}_{i}"
        customer2_runs.append(run)
    
    try:
        # Create datasets first
        await repository.create_dataset(dataset1)
        await repository.create_dataset(dataset2)
        
        # Create all evaluation runs in database
        for run in customer1_runs:
            await repository.create_evaluation_run(run)
        
        for run in customer2_runs:
            await repository.create_evaluation_run(run)
        
        # List evaluation runs for customer 1
        retrieved_customer1 = await repository.get_evaluation_runs(customer1_id)
        
        # List evaluation runs for customer 2
        retrieved_customer2 = await repository.get_evaluation_runs(customer2_id)
        
        # Property: Customer 1 should get exactly the number of runs they created
        assert len(retrieved_customer1) == num_runs_customer1, \
            f"Customer 1 should have {num_runs_customer1} runs, got {len(retrieved_customer1)}"
        
        # Property: Customer 2 should get exactly the number of runs they created
        assert len(retrieved_customer2) == num_runs_customer2, \
            f"Customer 2 should have {num_runs_customer2} runs, got {len(retrieved_customer2)}"
        
        # Property: All customer 1 run IDs should be in the retrieved list
        customer1_ids = {run.id for run in customer1_runs}
        retrieved_customer1_ids = {run.id for run in retrieved_customer1}
        
        assert customer1_ids == retrieved_customer1_ids, \
            f"Customer 1 run IDs mismatch. Expected: {customer1_ids}, Got: {retrieved_customer1_ids}"
        
        # Property: All customer 2 run IDs should be in the retrieved list
        customer2_ids = {run.id for run in customer2_runs}
        retrieved_customer2_ids = {run.id for run in retrieved_customer2}
        
        assert customer2_ids == retrieved_customer2_ids, \
            f"Customer 2 run IDs mismatch. Expected: {customer2_ids}, Got: {retrieved_customer2_ids}"
        
        # Property: Customer 1 should not see any of customer 2's runs
        assert customer1_ids.isdisjoint(retrieved_customer2_ids), \
            f"Customer 1 runs leaked into customer 2's list: {customer1_ids & retrieved_customer2_ids}"
        
        # Property: Customer 2 should not see any of customer 1's runs
        assert customer2_ids.isdisjoint(retrieved_customer1_ids), \
            f"Customer 2 runs leaked into customer 1's list: {customer2_ids & retrieved_customer1_ids}"
        
        # Property: All retrieved runs should have correct customer_id
        for run in retrieved_customer1:
            assert run.customer_id == customer1_id, \
                f"Run {run.id} has wrong customer_id: {run.customer_id}, expected {customer1_id}"
        
        for run in retrieved_customer2:
            assert run.customer_id == customer2_id, \
                f"Run {run.id} has wrong customer_id: {run.customer_id}, expected {customer2_id}"
        
        # Property: Retrieved runs should have all metadata intact
        for original, retrieved in zip(customer1_runs, retrieved_customer1):
            assert retrieved.dataset_id == original.dataset_id, \
                f"Run {retrieved.id} dataset_id mismatch"
            assert retrieved.application_profile_id == original.application_profile_id, \
                f"Run {retrieved.id} application_profile_id mismatch"
            assert retrieved.status == original.status, \
                f"Run {retrieved.id} status mismatch"
        
        for original, retrieved in zip(customer2_runs, retrieved_customer2):
            assert retrieved.dataset_id == original.dataset_id, \
                f"Run {retrieved.id} dataset_id mismatch"
            assert retrieved.application_profile_id == original.application_profile_id, \
                f"Run {retrieved.id} application_profile_id mismatch"
            assert retrieved.status == original.status, \
                f"Run {retrieved.id} status mismatch"
    
    finally:
        # Cleanup: Delete all test runs and datasets
        for run in customer1_runs:
            try:
                # Delete from database directly since there's no delete method in repository
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass  # Ignore cleanup errors
        
        for run in customer2_runs:
            try:
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass  # Ignore cleanup errors
        
        try:
            await repository.delete_dataset(dataset1_id, customer1_id)
        except Exception:
            pass
        
        try:
            await repository.delete_dataset(dataset2_id, customer2_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
async def test_list_empty_returns_empty_list(data):
    """
    Property 4: List operations return all entities (edge case: empty list).
    
    **Validates: Requirements 1.6, 1.7**
    
    For a customer with no datasets, listing datasets should return an empty list.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID that doesn't exist
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_nonexistent_{test_run_id}"
    
    # List datasets for non-existent customer
    retrieved_datasets = await repository.get_datasets(customer_id)
    
    # Property: Should return empty list, not None or error
    assert retrieved_datasets is not None, \
        "List operation should return a list, not None"
    
    assert isinstance(retrieved_datasets, list), \
        f"List operation should return a list, got {type(retrieved_datasets)}"
    
    assert len(retrieved_datasets) == 0, \
        f"Non-existent customer should have 0 datasets, got {len(retrieved_datasets)}"
    
    # List evaluation runs for non-existent customer
    retrieved_runs = await repository.get_evaluation_runs(customer_id)
    
    # Property: Should return empty list, not None or error
    assert retrieved_runs is not None, \
        "List operation should return a list, not None"
    
    assert isinstance(retrieved_runs, list), \
        f"List operation should return a list, got {type(retrieved_runs)}"
    
    assert len(retrieved_runs) == 0, \
        f"Non-existent customer should have 0 runs, got {len(retrieved_runs)}"
