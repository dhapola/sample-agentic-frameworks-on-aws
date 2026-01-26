"""Property-based tests for filtering and sorting operations.

Feature: gen-ai-eval-platform
Properties: Filtering returns only matching results, Sorting maintains order
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from typing import List

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.models.evaluation_run import EvaluationRun
from app.models.dataset import Dataset


# ==================== Hypothesis Strategies ====================

@st.composite
def evaluation_run_strategy(draw, customer_id: str, dataset_id: str, run_index: int):
    """Generate valid EvaluationRun objects with varied properties for filtering/sorting."""
    run_id = f"run_{customer_id}_{run_index}"
    profile_id = f"profile_{customer_id}_001"
    
    # Generate varied statuses for filtering tests
    status = draw(st.sampled_from(["pending", "running", "completed", "failed"]))
    
    # Generate varied timestamps for sorting tests
    # Use a base time and add random offsets to ensure different times
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    time_offset_minutes = draw(st.integers(min_value=0, max_value=1000))
    start_time = base_time + timedelta(minutes=time_offset_minutes)
    
    # End time only for completed/failed runs
    end_time = None
    if status in ["completed", "failed"]:
        end_offset_minutes = draw(st.integers(min_value=1, max_value=60))
        end_time = start_time + timedelta(minutes=end_offset_minutes)
    
    return EvaluationRun(
        id=run_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        application_profile_id=profile_id,
        status=status,
        start_time=start_time,
        end_time=end_time,
        responses=[],
        metrics=None
    )


# ==================== Helper Functions ====================

async def get_evaluation_runs_filtered(
    repository: DataRepository,
    customer_id: str,
    status_filter: str = None
) -> List[EvaluationRun]:
    """
    Get evaluation runs with optional status filtering.
    
    This simulates filtering functionality that should be available in the API.
    """
    all_runs = await repository.get_evaluation_runs(customer_id)
    
    if status_filter:
        return [run for run in all_runs if run.status == status_filter]
    
    return all_runs


async def get_evaluation_runs_sorted(
    repository: DataRepository,
    customer_id: str,
    sort_by: str = "start_time",
    sort_order: str = "asc"
) -> List[EvaluationRun]:
    """
    Get evaluation runs with sorting.
    
    This simulates sorting functionality that should be available in the API.
    
    Args:
        repository: Data repository
        customer_id: Customer ID for tenant isolation
        sort_by: Field to sort by ('start_time', 'status', 'id')
        sort_order: Sort order ('asc' or 'desc')
    """
    all_runs = await repository.get_evaluation_runs(customer_id)
    
    # Define sort key functions
    sort_keys = {
        "start_time": lambda r: r.start_time,
        "status": lambda r: r.status,
        "id": lambda r: r.id
    }
    
    if sort_by not in sort_keys:
        sort_by = "start_time"
    
    reverse = (sort_order == "desc")
    
    return sorted(all_runs, key=sort_keys[sort_by], reverse=reverse)


# ==================== Property Tests ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    num_runs=st.integers(min_value=3, max_value=10),
    filter_status=st.sampled_from(["pending", "running", "completed", "failed"]),
    data=st.data()
)
async def test_filtering_returns_only_matching_results(
    num_runs: int,
    filter_status: str,
    data
):
    """
    Property 18: Filtering returns only matching results.
    
    **Validates: Requirements 5.6**
    
    For any filter criteria applied to evaluation results, all returned results
    should match the filter criteria and no matching results should be excluded.
    
    This test verifies that:
    1. All returned runs have the filtered status
    2. No runs with the filtered status are excluded
    3. No runs with different statuses are included
    4. Filtering respects tenant isolation
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_filter_test_{test_run_id}"
    
    # Create a dataset for the runs
    dataset_id = f"dataset_{customer_id}_{test_run_id}"
    dataset = Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name="Test Dataset for Filtering",
        description="Dataset for filtering property test",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Generate evaluation runs with varied statuses
    runs = []
    for i in range(num_runs):
        run = data.draw(evaluation_run_strategy(customer_id, dataset_id, i))
        runs.append(run)
    
    # Count how many runs should match the filter
    expected_matching_count = sum(1 for run in runs if run.status == filter_status)
    
    try:
        # Create dataset
        await repository.create_dataset(dataset)
        
        # Create all evaluation runs
        for run in runs:
            await repository.create_evaluation_run(run)
        
        # Apply filter
        filtered_runs = await get_evaluation_runs_filtered(
            repository,
            customer_id,
            status_filter=filter_status
        )
        
        # Property 1: All returned runs must match the filter criteria
        for run in filtered_runs:
            assert run.status == filter_status, \
                f"Filtered run {run.id} has status '{run.status}', expected '{filter_status}'"
        
        # Property 2: The count of filtered runs should match expected count
        assert len(filtered_runs) == expected_matching_count, \
            f"Expected {expected_matching_count} runs with status '{filter_status}', got {len(filtered_runs)}"
        
        # Property 3: All runs with matching status should be included
        matching_run_ids = {run.id for run in runs if run.status == filter_status}
        filtered_run_ids = {run.id for run in filtered_runs}
        
        assert matching_run_ids == filtered_run_ids, \
            f"Missing runs in filtered results. Expected: {matching_run_ids}, Got: {filtered_run_ids}"
        
        # Property 4: No runs with different statuses should be included
        for run in filtered_runs:
            assert run.id in matching_run_ids, \
                f"Run {run.id} should not be in filtered results (status: {run.status})"
        
        # Property 5: All filtered runs should belong to the correct customer
        for run in filtered_runs:
            assert run.customer_id == customer_id, \
                f"Filtered run {run.id} has wrong customer_id: {run.customer_id}"
        
        # Property 6: Filtering should not modify the runs
        for run in filtered_runs:
            original = next(r for r in runs if r.id == run.id)
            assert run.dataset_id == original.dataset_id, \
                f"Run {run.id} dataset_id was modified during filtering"
            assert run.application_profile_id == original.application_profile_id, \
                f"Run {run.id} application_profile_id was modified during filtering"
    
    finally:
        # Cleanup
        for run in runs:
            try:
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass
        
        try:
            await repository.delete_dataset(dataset_id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=20, deadline=None)
@given(
    num_runs=st.integers(min_value=3, max_value=10),
    sort_by=st.sampled_from(["start_time", "status", "id"]),
    sort_order=st.sampled_from(["asc", "desc"]),
    data=st.data()
)
async def test_sorting_maintains_order(
    num_runs: int,
    sort_by: str,
    sort_order: str,
    data
):
    """
    Property 19: Sorting maintains order.
    
    **Validates: Requirements 5.6**
    
    For any sort criteria applied to evaluation results, the returned results
    should be ordered according to the criteria.
    
    This test verifies that:
    1. Results are sorted in the specified order
    2. All runs are included (sorting doesn't filter)
    3. Sorting respects tenant isolation
    4. Sorting doesn't modify the run data
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_sort_test_{test_run_id}"
    
    # Create a dataset for the runs
    dataset_id = f"dataset_{customer_id}_{test_run_id}"
    dataset = Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name="Test Dataset for Sorting",
        description="Dataset for sorting property test",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Generate evaluation runs with varied properties
    runs = []
    for i in range(num_runs):
        run = data.draw(evaluation_run_strategy(customer_id, dataset_id, i))
        runs.append(run)
    
    try:
        # Create dataset
        await repository.create_dataset(dataset)
        
        # Create all evaluation runs
        for run in runs:
            await repository.create_evaluation_run(run)
        
        # Apply sorting
        sorted_runs = await get_evaluation_runs_sorted(
            repository,
            customer_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Property 1: All runs should be included (sorting doesn't filter)
        assert len(sorted_runs) == num_runs, \
            f"Sorting should return all {num_runs} runs, got {len(sorted_runs)}"
        
        # Property 2: All original run IDs should be present
        original_ids = {run.id for run in runs}
        sorted_ids = {run.id for run in sorted_runs}
        
        assert original_ids == sorted_ids, \
            f"Sorted results missing runs. Expected: {original_ids}, Got: {sorted_ids}"
        
        # Property 3: Results should be in the correct order
        if sort_by == "start_time":
            for i in range(len(sorted_runs) - 1):
                current_time = sorted_runs[i].start_time
                next_time = sorted_runs[i + 1].start_time
                
                if sort_order == "asc":
                    assert current_time <= next_time, \
                        f"Ascending sort by start_time violated at index {i}: {current_time} > {next_time}"
                else:  # desc
                    assert current_time >= next_time, \
                        f"Descending sort by start_time violated at index {i}: {current_time} < {next_time}"
        
        elif sort_by == "status":
            for i in range(len(sorted_runs) - 1):
                current_status = sorted_runs[i].status
                next_status = sorted_runs[i + 1].status
                
                if sort_order == "asc":
                    assert current_status <= next_status, \
                        f"Ascending sort by status violated at index {i}: {current_status} > {next_status}"
                else:  # desc
                    assert current_status >= next_status, \
                        f"Descending sort by status violated at index {i}: {current_status} < {next_status}"
        
        elif sort_by == "id":
            for i in range(len(sorted_runs) - 1):
                current_id = sorted_runs[i].id
                next_id = sorted_runs[i + 1].id
                
                if sort_order == "asc":
                    assert current_id <= next_id, \
                        f"Ascending sort by id violated at index {i}: {current_id} > {next_id}"
                else:  # desc
                    assert current_id >= next_id, \
                        f"Descending sort by id violated at index {i}: {current_id} < {next_id}"
        
        # Property 4: All sorted runs should belong to the correct customer
        for run in sorted_runs:
            assert run.customer_id == customer_id, \
                f"Sorted run {run.id} has wrong customer_id: {run.customer_id}"
        
        # Property 5: Sorting should not modify the run data
        for sorted_run in sorted_runs:
            original = next(r for r in runs if r.id == sorted_run.id)
            assert sorted_run.status == original.status, \
                f"Run {sorted_run.id} status was modified during sorting"
            assert sorted_run.dataset_id == original.dataset_id, \
                f"Run {sorted_run.id} dataset_id was modified during sorting"
            assert sorted_run.application_profile_id == original.application_profile_id, \
                f"Run {sorted_run.id} application_profile_id was modified during sorting"
            assert sorted_run.start_time == original.start_time, \
                f"Run {sorted_run.id} start_time was modified during sorting"
    
    finally:
        # Cleanup
        for run in runs:
            try:
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass
        
        try:
            await repository.delete_dataset(dataset_id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    num_runs=st.integers(min_value=5, max_value=10),
    filter_status=st.sampled_from(["completed", "failed"]),
    sort_order=st.sampled_from(["asc", "desc"]),
    data=st.data()
)
async def test_filtering_and_sorting_combined(
    num_runs: int,
    filter_status: str,
    sort_order: str,
    data
):
    """
    Property 18 & 19 Combined: Filtering and sorting work together correctly.
    
    **Validates: Requirements 5.6**
    
    When both filtering and sorting are applied:
    1. Only matching results are returned (filtering)
    2. Results are in the correct order (sorting)
    3. No data is lost or corrupted
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_combined_test_{test_run_id}"
    
    # Create a dataset for the runs
    dataset_id = f"dataset_{customer_id}_{test_run_id}"
    dataset = Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name="Test Dataset for Combined Operations",
        description="Dataset for combined filtering and sorting test",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Generate evaluation runs
    runs = []
    for i in range(num_runs):
        run = data.draw(evaluation_run_strategy(customer_id, dataset_id, i))
        runs.append(run)
    
    # Count expected matching runs
    expected_matching = [run for run in runs if run.status == filter_status]
    expected_count = len(expected_matching)
    
    try:
        # Create dataset
        await repository.create_dataset(dataset)
        
        # Create all evaluation runs
        for run in runs:
            await repository.create_evaluation_run(run)
        
        # Apply filtering first
        filtered_runs = await get_evaluation_runs_filtered(
            repository,
            customer_id,
            status_filter=filter_status
        )
        
        # Then apply sorting to filtered results
        # Sort by start_time
        reverse = (sort_order == "desc")
        sorted_filtered_runs = sorted(filtered_runs, key=lambda r: r.start_time, reverse=reverse)
        
        # Property 1: Count should match expected
        assert len(sorted_filtered_runs) == expected_count, \
            f"Expected {expected_count} filtered runs, got {len(sorted_filtered_runs)}"
        
        # Property 2: All results should match filter
        for run in sorted_filtered_runs:
            assert run.status == filter_status, \
                f"Run {run.id} has wrong status: {run.status}, expected {filter_status}"
        
        # Property 3: Results should be sorted correctly
        for i in range(len(sorted_filtered_runs) - 1):
            current_time = sorted_filtered_runs[i].start_time
            next_time = sorted_filtered_runs[i + 1].start_time
            
            if sort_order == "asc":
                assert current_time <= next_time, \
                    f"Sort order violated at index {i}: {current_time} > {next_time}"
            else:  # desc
                assert current_time >= next_time, \
                    f"Sort order violated at index {i}: {current_time} < {next_time}"
        
        # Property 4: All expected runs should be present
        expected_ids = {run.id for run in expected_matching}
        result_ids = {run.id for run in sorted_filtered_runs}
        
        assert expected_ids == result_ids, \
            f"Missing runs. Expected: {expected_ids}, Got: {result_ids}"
        
        # Property 5: Tenant isolation maintained
        for run in sorted_filtered_runs:
            assert run.customer_id == customer_id, \
                f"Run {run.id} has wrong customer_id: {run.customer_id}"
    
    finally:
        # Cleanup
        for run in runs:
            try:
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass
        
        try:
            await repository.delete_dataset(dataset_id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
async def test_filtering_empty_results(data):
    """
    Property 18: Filtering with no matches returns empty list.
    
    **Validates: Requirements 5.6**
    
    When filtering with criteria that match no runs, should return empty list.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_empty_filter_{test_run_id}"
    
    # Create a dataset
    dataset_id = f"dataset_{customer_id}_{test_run_id}"
    dataset = Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name="Test Dataset",
        description="Dataset for empty filter test",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create runs with only "completed" status
    runs = []
    for i in range(3):
        run = EvaluationRun(
            id=f"run_{customer_id}_{i}",
            customer_id=customer_id,
            dataset_id=dataset_id,
            application_profile_id=f"profile_{customer_id}",
            status="completed",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            responses=[],
            metrics=None
        )
        runs.append(run)
    
    try:
        # Create dataset and runs
        await repository.create_dataset(dataset)
        for run in runs:
            await repository.create_evaluation_run(run)
        
        # Filter for "failed" status (which doesn't exist)
        filtered_runs = await get_evaluation_runs_filtered(
            repository,
            customer_id,
            status_filter="failed"
        )
        
        # Property: Should return empty list
        assert isinstance(filtered_runs, list), \
            f"Should return list, got {type(filtered_runs)}"
        
        assert len(filtered_runs) == 0, \
            f"Should return empty list for non-matching filter, got {len(filtered_runs)} runs"
    
    finally:
        # Cleanup
        for run in runs:
            try:
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass
        
        try:
            await repository.delete_dataset(dataset_id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
async def test_sorting_empty_list(data):
    """
    Property 19: Sorting empty list returns empty list.
    
    **Validates: Requirements 5.6**
    
    Sorting an empty list should return an empty list without errors.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID with no runs
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_empty_sort_{test_run_id}"
    
    # Sort empty list
    sorted_runs = await get_evaluation_runs_sorted(
        repository,
        customer_id,
        sort_by="start_time",
        sort_order="asc"
    )
    
    # Property: Should return empty list
    assert isinstance(sorted_runs, list), \
        f"Should return list, got {type(sorted_runs)}"
    
    assert len(sorted_runs) == 0, \
        f"Should return empty list for customer with no runs, got {len(sorted_runs)} runs"
