"""Property-based tests for dataset operations.

Feature: gen-ai-eval-platform
Properties: Dataset persistence, modification, deletion, and listing
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List

from app.database.repository import DataRepository
from app.models.dataset import Dataset
from app.models.test_case import TestCase


# ==================== Hypothesis Strategies ====================

@st.composite
def testcase_strategy(draw):
    """Generate valid TestCase objects."""
    tc_id = f"tc_{draw(st.integers(min_value=1000, max_value=9999))}"
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
def dataset_strategy(draw):
    """Generate valid Dataset objects."""
    dataset_id = f"dataset_{draw(st.integers(min_value=1000, max_value=9999))}"
    customer_id = f"cust_{draw(st.integers(min_value=1000, max_value=9999))}"
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    description = draw(st.text(max_size=500, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    
    # Generate 0-10 test cases
    num_test_cases = draw(st.integers(min_value=0, max_value=10))
    test_cases = []
    for i in range(num_test_cases):
        test_case = draw(testcase_strategy())
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
@settings(max_examples=100, deadline=None)
@given(dataset=dataset_strategy())
async def test_dataset_persistence_round_trip(dataset: Dataset):
    """
    Property 1: Dataset persistence round-trip.
    
    **Validates: Requirements 1.2, 1.8, 6.3**
    
    For any dataset with test cases, creating the dataset then retrieving it
    should return an equivalent dataset with all test cases intact.
    """
    # Create mock database
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.datasets = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Storage for the created dataset document
    stored_doc = {}
    
    # Mock insert_one to store the dataset
    async def mock_insert_one(doc):
        stored_doc.update(doc)
        result = MagicMock()
        result.inserted_id = doc["_id"]
        return result
    
    mock_database.datasets.insert_one = mock_insert_one
    
    # Mock find_one to retrieve the stored dataset
    async def mock_find_one(query):
        if query.get("_id") == dataset.id and query.get("customerId") == dataset.customer_id:
            return stored_doc.copy()
        return None
    
    mock_database.datasets.find_one = mock_find_one
    
    # Create the dataset
    created = await repository.create_dataset(dataset)
    
    # Verify creation succeeded
    assert created is not None, "Dataset creation should succeed"
    assert created.id == dataset.id
    assert created.customer_id == dataset.customer_id
    
    # Retrieve the dataset
    retrieved = await repository.get_dataset_by_id(dataset.id, dataset.customer_id)
    
    # Property: Retrieved dataset should not be None
    assert retrieved is not None, \
        f"Dataset {dataset.id} should be retrievable after creation"
    
    # Property: Retrieved dataset should have same ID
    assert retrieved.id == dataset.id, \
        f"Retrieved dataset ID {retrieved.id} should match original {dataset.id}"
    
    # Property: Retrieved dataset should have same customer_id
    assert retrieved.customer_id == dataset.customer_id, \
        f"Retrieved customer_id {retrieved.customer_id} should match original {dataset.customer_id}"
    
    # Property: Retrieved dataset should have same name
    assert retrieved.name == dataset.name, \
        f"Retrieved name '{retrieved.name}' should match original '{dataset.name}'"
    
    # Property: Retrieved dataset should have same description
    assert retrieved.description == dataset.description, \
        f"Retrieved description should match original"
    
    # Property: Retrieved dataset should have same number of test cases
    assert len(retrieved.test_cases) == len(dataset.test_cases), \
        f"Retrieved dataset has {len(retrieved.test_cases)} test cases, expected {len(dataset.test_cases)}"
    
    # Property: All test cases should be intact with correct data
    for i, (original_tc, retrieved_tc) in enumerate(zip(dataset.test_cases, retrieved.test_cases)):
        assert retrieved_tc.id == original_tc.id, \
            f"Test case {i}: ID mismatch - got {retrieved_tc.id}, expected {original_tc.id}"
        assert retrieved_tc.input == original_tc.input, \
            f"Test case {i}: Input mismatch"
        assert retrieved_tc.expected_output == original_tc.expected_output, \
            f"Test case {i}: Expected output mismatch"
    
    # Property: Test case order should be preserved
    retrieved_ids = [tc.id for tc in retrieved.test_cases]
    original_ids = [tc.id for tc in dataset.test_cases]
    assert retrieved_ids == original_ids, \
        f"Test case order not preserved: got {retrieved_ids}, expected {original_ids}"
