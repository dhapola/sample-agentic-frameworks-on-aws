"""Property-based tests for run comparison functionality.

Feature: gen-ai-eval-platform
Property 17: Run comparison returns all specified runs
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metrics import AggregatedMetrics


# ==================== Hypothesis Strategies ====================

@st.composite
def aggregated_metrics_strategy(draw, num_responses: int):
    """Generate valid AggregatedMetrics objects that match the number of responses."""
    failed = draw(st.integers(min_value=0, max_value=min(num_responses, 10)))
    return AggregatedMetrics(
        average_accuracy=draw(st.floats(min_value=0.0, max_value=1.0)),
        average_relevance=draw(st.floats(min_value=0.0, max_value=1.0)),
        average_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        median_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        p95_latency=draw(st.floats(min_value=0.1, max_value=10000.0)),
        success_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        total_test_cases=num_responses,  # Must match number of responses
        failed_test_cases=failed
    )


@st.composite
def evaluation_run_strategy(draw, customer_id: str, dataset_id: str, run_num: int):
    """Generate valid EvaluationRun objects with metrics."""
    run_id = f"run_{customer_id}_{run_num}"
    profile_id = f"profile_{customer_id}_001"
    status = draw(st.sampled_from(["completed", "failed"]))
    
    # For comparison tests, we don't need actual responses, just metrics
    # Set responses to empty list and metrics.total_test_cases to 0
    metrics = AggregatedMetrics(
        average_accuracy=draw(st.floats(min_value=0.0, max_value=1.0)),
        average_relevance=draw(st.floats(min_value=0.0, max_value=1.0)),
        average_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        median_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        p95_latency=draw(st.floats(min_value=0.1, max_value=10000.0)),
        success_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        total_test_cases=0,  # Match empty responses list
        failed_test_cases=0
    )
    
    return EvaluationRun(
        id=run_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        application_profile_id=profile_id,
        status=status,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        responses=[],
        metrics=metrics
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    num_runs=st.integers(min_value=2, max_value=5),
    data=st.data()
)
async def test_run_comparison_returns_all_specified_runs(
    num_runs: int,
    data
):
    """
    Property 17: Run comparison returns all specified runs.
    
    **Validates: Requirements 5.4**
    
    For any set of evaluation run IDs, requesting a comparison should return
    metrics for all specified runs with correct data and tenant isolation.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_test_{test_run_id}"
    
    # Create a dataset (required for evaluation runs)
    dataset_id = f"dataset_{customer_id}_{test_run_id}"
    dataset = Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name="Test Dataset",
        description="Test dataset for run comparison",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Generate evaluation runs
    evaluation_runs = []
    for i in range(num_runs):
        run = data.draw(evaluation_run_strategy(customer_id, dataset_id, i))
        evaluation_runs.append(run)
    
    try:
        # Create dataset first
        await repository.create_dataset(dataset)
        
        # Create all evaluation runs in database
        for run in evaluation_runs:
            await repository.create_evaluation_run(run)
        
        # Get all run IDs
        run_ids = [run.id for run in evaluation_runs]
        
        # Retrieve runs for comparison (simulating the compare_runs endpoint logic)
        retrieved_runs = []
        for run_id in run_ids:
            run = await repository.get_evaluation_run_by_id(run_id, customer_id)
            if run is not None:
                retrieved_runs.append(run)
        
        # Property: Should retrieve exactly the number of runs requested
        assert len(retrieved_runs) == num_runs, \
            f"Expected {num_runs} runs in comparison, got {len(retrieved_runs)}"
        
        # Property: All requested run IDs should be in the retrieved list
        retrieved_run_ids = {run.id for run in retrieved_runs}
        expected_run_ids = set(run_ids)
        
        assert retrieved_run_ids == expected_run_ids, \
            f"Run IDs mismatch. Expected: {expected_run_ids}, Got: {retrieved_run_ids}"
        
        # Property: All retrieved runs should belong to the correct customer
        for run in retrieved_runs:
            assert run.customer_id == customer_id, \
                f"Run {run.id} has wrong customer_id: {run.customer_id}, expected {customer_id}"
        
        # Property: All retrieved runs should have metrics
        for run in retrieved_runs:
            assert run.metrics is not None, \
                f"Run {run.id} should have metrics for comparison"
        
        # Property: Retrieved runs should have all required fields for comparison
        for run in retrieved_runs:
            assert run.id is not None, f"Run should have id"
            assert run.dataset_id is not None, f"Run {run.id} should have dataset_id"
            assert run.application_profile_id is not None, f"Run {run.id} should have application_profile_id"
            assert run.start_time is not None, f"Run {run.id} should have start_time"
            assert run.metrics is not None, f"Run {run.id} should have metrics"
        
        # Property: Metrics should have all required fields
        for run in retrieved_runs:
            metrics = run.metrics
            assert metrics.average_accuracy is not None, \
                f"Run {run.id} metrics should have average_accuracy"
            assert metrics.average_relevance is not None, \
                f"Run {run.id} metrics should have average_relevance"
            assert metrics.average_latency is not None, \
                f"Run {run.id} metrics should have average_latency"
            assert metrics.median_latency is not None, \
                f"Run {run.id} metrics should have median_latency"
            assert metrics.p95_latency is not None, \
                f"Run {run.id} metrics should have p95_latency"
            assert metrics.success_rate is not None, \
                f"Run {run.id} metrics should have success_rate"
            assert metrics.total_test_cases is not None, \
                f"Run {run.id} metrics should have total_test_cases"
            assert metrics.failed_test_cases is not None, \
                f"Run {run.id} metrics should have failed_test_cases"
        
        # Property: Retrieved runs should match original data
        for original, retrieved in zip(evaluation_runs, retrieved_runs):
            assert retrieved.id == original.id, \
                f"Run ID mismatch"
            assert retrieved.dataset_id == original.dataset_id, \
                f"Run {retrieved.id} dataset_id mismatch"
            assert retrieved.application_profile_id == original.application_profile_id, \
                f"Run {retrieved.id} application_profile_id mismatch"
            assert retrieved.status == original.status, \
                f"Run {retrieved.id} status mismatch"
            
            # Verify metrics match
            assert retrieved.metrics.average_accuracy == original.metrics.average_accuracy, \
                f"Run {retrieved.id} average_accuracy mismatch"
            assert retrieved.metrics.average_relevance == original.metrics.average_relevance, \
                f"Run {retrieved.id} average_relevance mismatch"
            assert retrieved.metrics.total_test_cases == original.metrics.total_test_cases, \
                f"Run {retrieved.id} total_test_cases mismatch"
    
    finally:
        # Cleanup: Delete all test runs and dataset
        for run in evaluation_runs:
            try:
                await database_manager.database.evaluationRuns.delete_one({"_id": run.id})
            except Exception:
                pass  # Ignore cleanup errors
        
        try:
            await repository.delete_dataset(dataset_id, customer_id)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    num_runs_customer1=st.integers(min_value=2, max_value=4),
    num_runs_customer2=st.integers(min_value=2, max_value=4),
    data=st.data()
)
async def test_run_comparison_enforces_tenant_isolation(
    num_runs_customer1: int,
    num_runs_customer2: int,
    data
):
    """
    Property 17: Run comparison enforces tenant isolation.
    
    **Validates: Requirements 5.4**
    
    When comparing runs, a customer should only be able to retrieve their own runs,
    not runs belonging to other customers.
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer IDs for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer1_id = f"cust_test_{test_run_id}_1"
    customer2_id = f"cust_test_{test_run_id}_2"
    
    # Create datasets for both customers
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
        run = data.draw(evaluation_run_strategy(customer1_id, dataset1_id, i))
        customer1_runs.append(run)
    
    # Generate evaluation runs for customer 2
    customer2_runs = []
    for i in range(num_runs_customer2):
        run = data.draw(evaluation_run_strategy(customer2_id, dataset2_id, i))
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
        
        # Get run IDs for both customers
        customer1_run_ids = [run.id for run in customer1_runs]
        customer2_run_ids = [run.id for run in customer2_runs]
        
        # Property: Customer 1 should be able to retrieve all their runs
        retrieved_customer1_runs = []
        for run_id in customer1_run_ids:
            run = await repository.get_evaluation_run_by_id(run_id, customer1_id)
            if run is not None:
                retrieved_customer1_runs.append(run)
        
        assert len(retrieved_customer1_runs) == num_runs_customer1, \
            f"Customer 1 should retrieve {num_runs_customer1} runs, got {len(retrieved_customer1_runs)}"
        
        # Property: Customer 2 should be able to retrieve all their runs
        retrieved_customer2_runs = []
        for run_id in customer2_run_ids:
            run = await repository.get_evaluation_run_by_id(run_id, customer2_id)
            if run is not None:
                retrieved_customer2_runs.append(run)
        
        assert len(retrieved_customer2_runs) == num_runs_customer2, \
            f"Customer 2 should retrieve {num_runs_customer2} runs, got {len(retrieved_customer2_runs)}"
        
        # Property: Customer 1 should NOT be able to retrieve customer 2's runs
        customer1_cannot_access_customer2 = []
        for run_id in customer2_run_ids:
            run = await repository.get_evaluation_run_by_id(run_id, customer1_id)
            if run is not None:
                customer1_cannot_access_customer2.append(run)
        
        assert len(customer1_cannot_access_customer2) == 0, \
            f"Customer 1 should not access customer 2's runs, but accessed {len(customer1_cannot_access_customer2)}"
        
        # Property: Customer 2 should NOT be able to retrieve customer 1's runs
        customer2_cannot_access_customer1 = []
        for run_id in customer1_run_ids:
            run = await repository.get_evaluation_run_by_id(run_id, customer2_id)
            if run is not None:
                customer2_cannot_access_customer1.append(run)
        
        assert len(customer2_cannot_access_customer1) == 0, \
            f"Customer 2 should not access customer 1's runs, but accessed {len(customer2_cannot_access_customer1)}"
        
        # Property: All retrieved runs for customer 1 should have customer1_id
        for run in retrieved_customer1_runs:
            assert run.customer_id == customer1_id, \
                f"Run {run.id} should belong to customer 1"
        
        # Property: All retrieved runs for customer 2 should have customer2_id
        for run in retrieved_customer2_runs:
            assert run.customer_id == customer2_id, \
                f"Run {run.id} should belong to customer 2"
    
    finally:
        # Cleanup: Delete all test runs and datasets
        for run in customer1_runs:
            try:
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
async def test_run_comparison_with_nonexistent_run(data):
    """
    Property 17: Run comparison handles nonexistent runs correctly.
    
    **Validates: Requirements 5.4**
    
    When requesting comparison with a nonexistent run ID, the system should
    return None for that run (allowing the API layer to handle the error).
    """
    # Connect to database
    await database_manager.connect()
    repository = DataRepository(database_manager.database)
    
    # Generate unique customer ID for this test run
    test_run_id = data.draw(st.integers(min_value=10000, max_value=99999))
    customer_id = f"cust_test_{test_run_id}"
    
    # Create a dataset (required for evaluation runs)
    dataset_id = f"dataset_{customer_id}_{test_run_id}"
    dataset = Dataset(
        id=dataset_id,
        customer_id=customer_id,
        name="Test Dataset",
        description="Test dataset for run comparison",
        test_cases=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Generate one valid evaluation run
    valid_run = data.draw(evaluation_run_strategy(customer_id, dataset_id, 0))
    
    # Generate a nonexistent run ID
    nonexistent_run_id = f"run_nonexistent_{test_run_id}"
    
    try:
        # Create dataset and valid run
        await repository.create_dataset(dataset)
        await repository.create_evaluation_run(valid_run)
        
        # Try to retrieve the valid run
        retrieved_valid = await repository.get_evaluation_run_by_id(valid_run.id, customer_id)
        
        # Property: Valid run should be retrieved successfully
        assert retrieved_valid is not None, \
            f"Valid run {valid_run.id} should be retrieved"
        
        # Try to retrieve the nonexistent run
        retrieved_nonexistent = await repository.get_evaluation_run_by_id(nonexistent_run_id, customer_id)
        
        # Property: Nonexistent run should return None
        assert retrieved_nonexistent is None, \
            f"Nonexistent run {nonexistent_run_id} should return None"
        
        # Property: Attempting to compare with mix of valid and invalid IDs
        # should allow the API layer to detect and handle the missing run
        run_ids = [valid_run.id, nonexistent_run_id]
        retrieved_runs = []
        
        for run_id in run_ids:
            run = await repository.get_evaluation_run_by_id(run_id, customer_id)
            if run is not None:
                retrieved_runs.append(run)
        
        # Property: Should only retrieve the valid run
        assert len(retrieved_runs) == 1, \
            f"Should retrieve only 1 valid run, got {len(retrieved_runs)}"
        
        assert retrieved_runs[0].id == valid_run.id, \
            f"Retrieved run should be the valid run"
    
    finally:
        # Cleanup
        try:
            await database_manager.database.evaluationRuns.delete_one({"_id": valid_run.id})
        except Exception:
            pass
        
        try:
            await repository.delete_dataset(dataset_id, customer_id)
        except Exception:
            pass
