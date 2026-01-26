"""Property-based tests for evaluation run persistence.

Feature: gen-ai-eval-platform
Property 12: Evaluation run persistence round-trip
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from typing import Optional

from app.database.repository import DataRepository
from app.models.evaluation_run import EvaluationRun
from app.models.response import Response
from app.models.metrics import AggregatedMetrics, IndividualMetrics


# ==================== Hypothesis Strategies ====================

@st.composite
def individual_metrics_strategy(draw):
    """Generate valid IndividualMetrics objects."""
    # Accuracy is optional (only when expected output exists)
    accuracy = draw(st.one_of(
        st.none(),
        st.floats(min_value=0.0, max_value=1.0)
    ))
    relevance = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return IndividualMetrics(
        accuracy=accuracy,
        relevance=relevance
    )


@st.composite
def response_strategy(draw):
    """Generate valid Response objects."""
    test_case_id = f"tc_{draw(st.integers(min_value=1000, max_value=9999))}"
    input_text = draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    output_text = draw(st.text(max_size=300, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    latency = draw(st.floats(min_value=0.1, max_value=5000.0))
    
    # Randomly include error or not
    has_error = draw(st.booleans())
    error = None
    if has_error:
        error = draw(st.sampled_from([
            "Connection timeout",
            "HTTP 500 Internal Server Error",
            "Application unavailable",
            "Invalid response format"
        ]))
        output_text = ""  # Empty output when there's an error
    
    # Generate timestamp
    timestamp = datetime.utcnow() - timedelta(seconds=draw(st.integers(min_value=0, max_value=3600)))
    
    # Optionally include individual metrics
    individual_metrics = None
    if not has_error:
        individual_metrics = draw(st.one_of(
            st.none(),
            individual_metrics_strategy()
        ))
    
    return Response(
        test_case_id=test_case_id,
        input=input_text.strip() or "test input",
        output=output_text.strip() if not has_error else "",
        latency=latency,
        timestamp=timestamp,
        error=error,
        individual_metrics=individual_metrics
    )


@st.composite
def aggregated_metrics_strategy(draw, num_responses: int):
    """Generate valid AggregatedMetrics objects."""
    # Ensure metrics are consistent with number of responses
    failed_test_cases = draw(st.integers(min_value=0, max_value=num_responses))
    
    return AggregatedMetrics(
        average_accuracy=draw(st.floats(min_value=0.0, max_value=1.0)),
        average_relevance=draw(st.floats(min_value=0.0, max_value=1.0)),
        average_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        median_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        p95_latency=draw(st.floats(min_value=0.1, max_value=5000.0)),
        success_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        total_test_cases=num_responses,
        failed_test_cases=failed_test_cases
    )


@st.composite
def evaluation_run_strategy(draw):
    """Generate valid EvaluationRun objects."""
    run_id = f"run_{draw(st.integers(min_value=1000, max_value=9999))}"
    customer_id = f"cust_{draw(st.integers(min_value=1000, max_value=9999))}"
    dataset_id = f"dataset_{draw(st.integers(min_value=1000, max_value=9999))}"
    profile_id = f"profile_{draw(st.integers(min_value=1000, max_value=9999))}"
    
    # Generate status
    status = draw(st.sampled_from(["pending", "running", "completed", "failed"]))
    
    # Generate timestamps
    start_time = datetime.utcnow() - timedelta(minutes=draw(st.integers(min_value=5, max_value=60)))
    
    # End time only for completed or failed runs
    end_time = None
    if status in ["completed", "failed"]:
        end_time = start_time + timedelta(seconds=draw(st.integers(min_value=10, max_value=300)))
    
    # Generate 0-10 responses
    num_responses = draw(st.integers(min_value=0, max_value=10))
    responses = []
    for i in range(num_responses):
        response = draw(response_strategy())
        # Ensure unique test_case_ids within the run
        response.test_case_id = f"{run_id}_tc_{i}"
        responses.append(response)
    
    # Generate metrics only for completed runs with responses
    metrics = None
    if status == "completed" and num_responses > 0:
        metrics = draw(st.one_of(
            st.none(),
            aggregated_metrics_strategy(num_responses)
        ))
    
    return EvaluationRun(
        id=run_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        application_profile_id=profile_id,
        status=status,
        start_time=start_time,
        end_time=end_time,
        responses=responses,
        metrics=metrics
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(evaluation_run=evaluation_run_strategy())
async def test_evaluation_run_persistence_round_trip(evaluation_run: EvaluationRun):
    """
    Property 12: Evaluation run persistence round-trip.
    
    **Validates: Requirements 3.6, 6.5**
    
    For any evaluation run with responses, storing the run then retrieving it
    should return an equivalent run with all responses and timestamps intact.
    """
    # Create mock database
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.evaluationRuns = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Storage for the created evaluation run document
    stored_doc = {}
    
    # Mock insert_one to store the evaluation run
    async def mock_insert_one(doc):
        stored_doc.update(doc)
        result = MagicMock()
        result.inserted_id = doc["_id"]
        return result
    
    mock_database.evaluationRuns.insert_one = mock_insert_one
    
    # Mock find_one to retrieve the stored evaluation run
    async def mock_find_one(query):
        if query.get("_id") == evaluation_run.id and query.get("customerId") == evaluation_run.customer_id:
            return stored_doc.copy()
        return None
    
    mock_database.evaluationRuns.find_one = mock_find_one
    
    # Create the evaluation run
    created = await repository.create_evaluation_run(evaluation_run)
    
    # Verify creation succeeded
    assert created is not None, "Evaluation run creation should succeed"
    assert created.id == evaluation_run.id
    assert created.customer_id == evaluation_run.customer_id
    
    # Retrieve the evaluation run
    retrieved = await repository.get_evaluation_run_by_id(evaluation_run.id, evaluation_run.customer_id)
    
    # Property: Retrieved evaluation run should not be None
    assert retrieved is not None, \
        f"Evaluation run {evaluation_run.id} should be retrievable after creation"
    
    # Property: Retrieved run should have same ID
    assert retrieved.id == evaluation_run.id, \
        f"Retrieved run ID {retrieved.id} should match original {evaluation_run.id}"
    
    # Property: Retrieved run should have same customer_id (tenant isolation)
    assert retrieved.customer_id == evaluation_run.customer_id, \
        f"Retrieved customer_id {retrieved.customer_id} should match original {evaluation_run.customer_id}"
    
    # Property: Retrieved run should have same dataset_id
    assert retrieved.dataset_id == evaluation_run.dataset_id, \
        f"Retrieved dataset_id {retrieved.dataset_id} should match original {evaluation_run.dataset_id}"
    
    # Property: Retrieved run should have same application_profile_id
    assert retrieved.application_profile_id == evaluation_run.application_profile_id, \
        f"Retrieved application_profile_id should match original"
    
    # Property: Retrieved run should have same status
    assert retrieved.status == evaluation_run.status, \
        f"Retrieved status {retrieved.status} should match original {evaluation_run.status}"
    
    # Property: Retrieved run should have same start_time (timestamps intact)
    assert retrieved.start_time is not None, "Start time should not be None"
    # Compare timestamps with small tolerance for serialization
    time_diff = abs((retrieved.start_time - evaluation_run.start_time).total_seconds())
    assert time_diff < 1.0, \
        f"Retrieved start_time should match original (diff: {time_diff}s)"
    
    # Property: Retrieved run should have same end_time if it exists
    if evaluation_run.end_time is not None:
        assert retrieved.end_time is not None, "End time should not be None when original has end_time"
        time_diff = abs((retrieved.end_time - evaluation_run.end_time).total_seconds())
        assert time_diff < 1.0, \
            f"Retrieved end_time should match original (diff: {time_diff}s)"
    else:
        assert retrieved.end_time is None, "End time should be None when original has no end_time"
    
    # Property: Retrieved run should have same number of responses
    assert len(retrieved.responses) == len(evaluation_run.responses), \
        f"Retrieved run has {len(retrieved.responses)} responses, expected {len(evaluation_run.responses)}"
    
    # Property: All responses should be intact with correct data
    for i, (original_resp, retrieved_resp) in enumerate(zip(evaluation_run.responses, retrieved.responses)):
        assert retrieved_resp.test_case_id == original_resp.test_case_id, \
            f"Response {i}: test_case_id mismatch - got {retrieved_resp.test_case_id}, expected {original_resp.test_case_id}"
        
        assert retrieved_resp.input == original_resp.input, \
            f"Response {i}: input mismatch"
        
        assert retrieved_resp.output == original_resp.output, \
            f"Response {i}: output mismatch"
        
        # Property: Latency should be preserved
        assert abs(retrieved_resp.latency - original_resp.latency) < 0.01, \
            f"Response {i}: latency mismatch - got {retrieved_resp.latency}, expected {original_resp.latency}"
        
        # Property: Timestamp should be preserved
        assert retrieved_resp.timestamp is not None, \
            f"Response {i}: timestamp should not be None"
        time_diff = abs((retrieved_resp.timestamp - original_resp.timestamp).total_seconds())
        assert time_diff < 1.0, \
            f"Response {i}: timestamp mismatch (diff: {time_diff}s)"
        
        # Property: Error should be preserved
        assert retrieved_resp.error == original_resp.error, \
            f"Response {i}: error mismatch - got {retrieved_resp.error}, expected {original_resp.error}"
        
        # Property: Individual metrics should be preserved if present
        if original_resp.individual_metrics is not None:
            assert retrieved_resp.individual_metrics is not None, \
                f"Response {i}: individual_metrics should not be None"
            
            if original_resp.individual_metrics.accuracy is not None:
                assert retrieved_resp.individual_metrics.accuracy is not None, \
                    f"Response {i}: accuracy should not be None"
                assert abs(retrieved_resp.individual_metrics.accuracy - original_resp.individual_metrics.accuracy) < 0.01, \
                    f"Response {i}: accuracy mismatch"
            else:
                assert retrieved_resp.individual_metrics.accuracy is None, \
                    f"Response {i}: accuracy should be None"
            
            assert abs(retrieved_resp.individual_metrics.relevance - original_resp.individual_metrics.relevance) < 0.01, \
                f"Response {i}: relevance mismatch"
        else:
            assert retrieved_resp.individual_metrics is None, \
                f"Response {i}: individual_metrics should be None when original has none"
    
    # Property: Response order should be preserved
    retrieved_test_case_ids = [r.test_case_id for r in retrieved.responses]
    original_test_case_ids = [r.test_case_id for r in evaluation_run.responses]
    assert retrieved_test_case_ids == original_test_case_ids, \
        f"Response order not preserved: got {retrieved_test_case_ids}, expected {original_test_case_ids}"
    
    # Property: Aggregated metrics should be preserved if present
    if evaluation_run.metrics is not None:
        assert retrieved.metrics is not None, "Metrics should not be None when original has metrics"
        
        assert abs(retrieved.metrics.average_accuracy - evaluation_run.metrics.average_accuracy) < 0.01, \
            "Average accuracy mismatch"
        assert abs(retrieved.metrics.average_relevance - evaluation_run.metrics.average_relevance) < 0.01, \
            "Average relevance mismatch"
        assert abs(retrieved.metrics.average_latency - evaluation_run.metrics.average_latency) < 0.01, \
            "Average latency mismatch"
        assert abs(retrieved.metrics.median_latency - evaluation_run.metrics.median_latency) < 0.01, \
            "Median latency mismatch"
        assert abs(retrieved.metrics.p95_latency - evaluation_run.metrics.p95_latency) < 0.01, \
            "P95 latency mismatch"
        assert abs(retrieved.metrics.success_rate - evaluation_run.metrics.success_rate) < 0.01, \
            "Success rate mismatch"
        assert retrieved.metrics.total_test_cases == evaluation_run.metrics.total_test_cases, \
            "Total test cases mismatch"
        assert retrieved.metrics.failed_test_cases == evaluation_run.metrics.failed_test_cases, \
            "Failed test cases mismatch"
    else:
        assert retrieved.metrics is None, "Metrics should be None when original has no metrics"
