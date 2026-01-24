"""Property-based tests for deletion operations with tenant isolation.

Feature: gen-ai-eval-platform
Property: Deletion removes entity completely
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.models.dataset import Dataset
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
    
    # Generate 1-5 test cases (at least 1 for deletion testing)
    num_test_cases = draw(st.integers(min_value=1, max_value=5))
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


# ==================== Property Tests ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    num_datasets=st.integers(min_value=1, max_value=5),
    data=st.data()
)
async def test_dataset_deletion_removes_entity_completely(
    num_datasets: int,
    data
):
    """
    Property 3: Deletion removes entity completely (datasets).
    
    **Validates: Requirements 1.4, 1.5**
    
    For any dataset, after deletion, attempting to retrieve that dataset
    should return None (not found). The dataset should be completely removed
    from the database with no orphaned data.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_test_del_{test_run_id}"
    
    # Generate datasets for the customer
    datasets = []
    for i in range(num_datasets):
        dataset = data.draw(dataset_strategy(customer_id))
        # Ensure unique dataset ID
        dataset.id = f"dataset_{customer_id}_{test_run_id}_{i}"
        datasets.append(dataset)
    
    try:
        # Create all datasets in database
        for dataset in datasets:
            await repository.create_dataset(dataset)
        
        # Verify all datasets were created
        retrieved_before = await repository.get_datasets(customer_id)
        assert len(retrieved_before) == num_datasets, \
            f"Expected {num_datasets} datasets before deletion, got {len(retrieved_before)}"
        
        # Delete each dataset one by one and verify deletion
        for i, dataset in enumerate(datasets):
            # Delete the dataset
            await repository.delete_dataset(dataset.id, customer_id)
            
            # Property: After deletion, retrieving the dataset should return None
            retrieved_deleted = await repository.get_dataset_by_id(dataset.id, customer_id)
            assert retrieved_deleted is None, \
                f"Dataset {dataset.id} should return None after deletion, got {retrieved_deleted}"
            
            # Property: The dataset should not appear in the list
            remaining_datasets = await repository.get_datasets(customer_id)
            remaining_ids = {ds.id for ds in remaining_datasets}
            assert dataset.id not in remaining_ids, \
                f"Deleted dataset {dataset.id} still appears in list: {remaining_ids}"
            
            # Property: The number of remaining datasets should decrease
            expected_remaining = num_datasets - (i + 1)
            assert len(remaining_datasets) == expected_remaining, \
                f"Expected {expected_remaining} datasets remaining, got {len(remaining_datasets)}"
            
            # Property: Only the deleted dataset should be gone, others should remain
            for other_dataset in datasets[i+1:]:
                assert other_dataset.id in remaining_ids, \
                    f"Non-deleted dataset {other_dataset.id} should still exist"
        
        # Property: After all deletions, list should be empty
        final_datasets = await repository.get_datasets(customer_id)
        assert len(final_datasets) == 0, \
            f"All datasets should be deleted, but {len(final_datasets)} remain"
        
        # Property: Attempting to delete an already deleted dataset should raise ValueError
        for dataset in datasets:
            with pytest.raises(ValueError, match=f"Dataset with ID {dataset.id} not found"):
                await repository.delete_dataset(dataset.id, customer_id)
    
    finally:
        # Cleanup: Ensure all test datasets are removed
        for dataset in datasets:
            try:
                await repository.delete_dataset(dataset.id, customer_id)
            except Exception:
                pass  # Ignore cleanup errors


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(data=st.data())
async def test_dataset_deletion_enforces_tenant_isolation(data):
    """
    Property 3: Deletion removes entity completely (tenant isolation).
    
    **Validates: Requirements 1.4, 1.5**
    
    For any dataset belonging to customer A, attempting to delete it using
    customer B's credentials should fail and leave the dataset intact.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_a_id = f"cust_test_del_a_{test_run_id}"
    customer_b_id = f"cust_test_del_b_{test_run_id}"
    
    # Generate dataset for customer A
    dataset_a = data.draw(dataset_strategy(customer_a_id))
    dataset_a.id = f"dataset_{customer_a_id}_{test_run_id}"
    
    try:
        # Create dataset for customer A
        await repository.create_dataset(dataset_a)
        
        # Verify dataset was created
        retrieved = await repository.get_dataset_by_id(dataset_a.id, customer_a_id)
        assert retrieved is not None, "Dataset should be created"
        assert retrieved.id == dataset_a.id
        
        # Property: Attempting to delete customer A's dataset using customer B's ID should fail
        with pytest.raises(ValueError, match=f"Dataset with ID {dataset_a.id} not found for customer {customer_b_id}"):
            await repository.delete_dataset(dataset_a.id, customer_b_id)
        
        # Property: After failed deletion attempt, dataset should still exist for customer A
        still_exists = await repository.get_dataset_by_id(dataset_a.id, customer_a_id)
        assert still_exists is not None, \
            f"Dataset {dataset_a.id} should still exist after failed cross-tenant deletion"
        assert still_exists.id == dataset_a.id
        assert still_exists.customer_id == customer_a_id
        
        # Property: Customer A should still be able to delete their own dataset
        await repository.delete_dataset(dataset_a.id, customer_a_id)
        
        # Verify deletion succeeded
        deleted = await repository.get_dataset_by_id(dataset_a.id, customer_a_id)
        assert deleted is None, "Dataset should be deleted after proper deletion"
    
    finally:
        # Cleanup
        try:
            await repository.delete_dataset(dataset_a.id, customer_a_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
async def test_dataset_deletion_removes_test_cases(data):
    """
    Property 3: Deletion removes entity completely (cascading deletion).
    
    **Validates: Requirements 1.4, 1.5**
    
    For any dataset with test cases, deleting the dataset should also remove
    all associated test cases. No orphaned test case data should remain.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_test_del_cascade_{test_run_id}"
    
    # Generate dataset with test cases
    dataset = data.draw(dataset_strategy(customer_id))
    dataset.id = f"dataset_{customer_id}_{test_run_id}"
    
    # Ensure dataset has test cases
    num_test_cases = len(dataset.test_cases)
    assert num_test_cases > 0, "Dataset should have test cases for this test"
    
    try:
        # Create dataset with test cases
        await repository.create_dataset(dataset)
        
        # Verify dataset and test cases were created
        retrieved = await repository.get_dataset_by_id(dataset.id, customer_id)
        assert retrieved is not None, "Dataset should be created"
        assert len(retrieved.test_cases) == num_test_cases, \
            f"Expected {num_test_cases} test cases, got {len(retrieved.test_cases)}"
        
        # Store test case IDs for verification
        test_case_ids = [tc.id for tc in retrieved.test_cases]
        
        # Delete the dataset
        await repository.delete_dataset(dataset.id, customer_id)
        
        # Property: After deletion, dataset should not exist
        deleted_dataset = await repository.get_dataset_by_id(dataset.id, customer_id)
        assert deleted_dataset is None, "Dataset should be deleted"
        
        # Property: Test cases should be removed with the dataset (no orphaned data)
        # Since test cases are embedded in the dataset document, they should be gone
        # Verify by checking that the dataset document is completely removed
        raw_doc = await database_manager.database.datasets.find_one({"_id": dataset.id})
        assert raw_doc is None, \
            f"Dataset document should be completely removed from database, but found: {raw_doc}"
        
        # Property: No test case data should be accessible
        # (In this implementation, test cases are embedded, so this is implicit)
        # But we verify the entire document is gone
        all_datasets = await repository.get_datasets(customer_id)
        for ds in all_datasets:
            for tc in ds.test_cases:
                assert tc.id not in test_case_ids, \
                    f"Test case {tc.id} from deleted dataset found in another dataset"
    
    finally:
        # Cleanup
        try:
            await repository.delete_dataset(dataset.id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
async def test_deletion_idempotency(data):
    """
    Property 3: Deletion removes entity completely (idempotency check).
    
    **Validates: Requirements 1.4, 1.5**
    
    For any dataset, attempting to delete it multiple times should fail
    after the first successful deletion (not be silently idempotent).
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_test_del_idemp_{test_run_id}"
    
    # Generate dataset
    dataset = data.draw(dataset_strategy(customer_id))
    dataset.id = f"dataset_{customer_id}_{test_run_id}"
    
    try:
        # Create dataset
        await repository.create_dataset(dataset)
        
        # Verify dataset exists
        retrieved = await repository.get_dataset_by_id(dataset.id, customer_id)
        assert retrieved is not None, "Dataset should be created"
        
        # First deletion should succeed
        await repository.delete_dataset(dataset.id, customer_id)
        
        # Verify dataset is gone
        deleted = await repository.get_dataset_by_id(dataset.id, customer_id)
        assert deleted is None, "Dataset should be deleted"
        
        # Property: Second deletion attempt should raise ValueError (not found)
        with pytest.raises(ValueError, match=f"Dataset with ID {dataset.id} not found"):
            await repository.delete_dataset(dataset.id, customer_id)
        
        # Property: Third deletion attempt should also fail
        with pytest.raises(ValueError, match=f"Dataset with ID {dataset.id} not found"):
            await repository.delete_dataset(dataset.id, customer_id)
        
        # Property: Dataset should still not exist after multiple failed deletion attempts
        still_deleted = await repository.get_dataset_by_id(dataset.id, customer_id)
        assert still_deleted is None, "Dataset should remain deleted"
    
    finally:
        # Cleanup
        try:
            await repository.delete_dataset(dataset.id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
async def test_deletion_with_nonexistent_id(data):
    """
    Property 3: Deletion removes entity completely (nonexistent entity).
    
    **Validates: Requirements 1.4, 1.5**
    
    For any nonexistent dataset ID, attempting to delete it should raise
    ValueError indicating the entity was not found.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID and nonexistent dataset ID
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_test_del_nonex_{test_run_id}"
    nonexistent_id = f"dataset_nonexistent_{test_run_id}"
    
    # Property: Attempting to delete nonexistent dataset should raise ValueError
    with pytest.raises(ValueError, match=f"Dataset with ID {nonexistent_id} not found"):
        await repository.delete_dataset(nonexistent_id, customer_id)
    
    # Property: After failed deletion, the dataset should still not exist
    retrieved = await repository.get_dataset_by_id(nonexistent_id, customer_id)
    assert retrieved is None, "Nonexistent dataset should remain nonexistent"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(
    num_datasets_customer1=st.integers(min_value=2, max_value=5),
    num_datasets_customer2=st.integers(min_value=2, max_value=5),
    data=st.data()
)
async def test_deletion_does_not_affect_other_customers(
    num_datasets_customer1: int,
    num_datasets_customer2: int,
    data
):
    """
    Property 3: Deletion removes entity completely (multi-tenant isolation).
    
    **Validates: Requirements 1.4, 1.5**
    
    For any dataset belonging to customer A, deleting it should not affect
    any datasets belonging to customer B. Tenant isolation must be maintained.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer1_id = f"cust_test_del_mt1_{test_run_id}"
    customer2_id = f"cust_test_del_mt2_{test_run_id}"
    
    # Generate datasets for both customers
    customer1_datasets = []
    for i in range(num_datasets_customer1):
        dataset = data.draw(dataset_strategy(customer1_id))
        dataset.id = f"dataset_{customer1_id}_{test_run_id}_{i}"
        customer1_datasets.append(dataset)
    
    customer2_datasets = []
    for i in range(num_datasets_customer2):
        dataset = data.draw(dataset_strategy(customer2_id))
        dataset.id = f"dataset_{customer2_id}_{test_run_id}_{i}"
        customer2_datasets.append(dataset)
    
    try:
        # Create all datasets
        for dataset in customer1_datasets:
            await repository.create_dataset(dataset)
        
        for dataset in customer2_datasets:
            await repository.create_dataset(dataset)
        
        # Verify initial state
        customer1_before = await repository.get_datasets(customer1_id)
        customer2_before = await repository.get_datasets(customer2_id)
        
        assert len(customer1_before) == num_datasets_customer1
        assert len(customer2_before) == num_datasets_customer2
        
        # Delete all datasets for customer 1
        for dataset in customer1_datasets:
            await repository.delete_dataset(dataset.id, customer1_id)
        
        # Property: Customer 1 should have no datasets
        customer1_after = await repository.get_datasets(customer1_id)
        assert len(customer1_after) == 0, \
            f"Customer 1 should have 0 datasets after deletion, got {len(customer1_after)}"
        
        # Property: Customer 2 should still have all their datasets
        customer2_after = await repository.get_datasets(customer2_id)
        assert len(customer2_after) == num_datasets_customer2, \
            f"Customer 2 should still have {num_datasets_customer2} datasets, got {len(customer2_after)}"
        
        # Property: Customer 2's dataset IDs should be unchanged
        customer2_ids_before = {ds.id for ds in customer2_before}
        customer2_ids_after = {ds.id for ds in customer2_after}
        assert customer2_ids_before == customer2_ids_after, \
            f"Customer 2's dataset IDs changed after customer 1's deletions"
        
        # Property: Customer 2's datasets should have intact data
        for original, retrieved in zip(customer2_datasets, customer2_after):
            assert retrieved.name == original.name
            assert retrieved.description == original.description
            assert len(retrieved.test_cases) == len(original.test_cases)
    
    finally:
        # Cleanup
        for dataset in customer1_datasets:
            try:
                await repository.delete_dataset(dataset.id, customer1_id)
            except Exception:
                pass
        
        for dataset in customer2_datasets:
            try:
                await repository.delete_dataset(dataset.id, customer2_id)
            except Exception:
                pass
