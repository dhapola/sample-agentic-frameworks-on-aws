"""Property-based tests for evaluation engine operations.

Feature: gen-ai-eval-platform
Properties: Evaluation execution, response metadata, partial failure resilience,
           metrics calculation, and metrics aggregation
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from app.engine.evaluation_engine import EvaluationEngine
from app.engine.metrics_calculator import MetricsCalculator
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.response import Response
from app.models.test_case import TestCase
from app.connectors.plugin import ApplicationResponse


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
def dataset_with_testcases_strategy(draw):
    """Generate valid Dataset objects with at least 1 test case."""
    dataset_id = f"dataset_{draw(st.integers(min_value=1000, max_value=9999))}"
    customer_id = f"cust_{draw(st.integers(min_value=1000, max_value=9999))}"
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    description = draw(st.text(max_size=500, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    
    # Generate 1-10 test cases (at least 1)
    num_test_cases = draw(st.integers(min_value=1, max_value=10))
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


@st.composite
def application_profile_strategy(draw, customer_id: str):
    """Generate valid ApplicationProfile objects."""
    profile_id = f"profile_{draw(st.integers(min_value=1000, max_value=9999))}"
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    app_type = draw(st.sampled_from(['chatbot', 'rag', 'agent', 'workflow', 'http']))
    
    return ApplicationProfile(
        id=profile_id,
        customer_id=customer_id,
        name=name.strip() or "Test Application",
        type=app_type,
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@st.composite
def response_strategy(draw, test_case: TestCase, include_error: bool = False):
    """Generate valid Response objects."""
    output = draw(st.text(max_size=300, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
    )))
    latency = draw(st.floats(min_value=0.1, max_value=5000.0))
    
    error = None
    if include_error:
        error = draw(st.one_of(
            st.none(),
            st.sampled_from([
                "Connection timeout",
                "HTTP 500 Internal Server Error",
                "Application unavailable",
                "Invalid response format"
            ])
        ))
    
    return Response(
        test_case_id=test_case.id,
        input=test_case.input,
        output=output.strip() if not error else "",
        latency=latency,
        timestamp=datetime.utcnow(),
        error=error
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(dataset=dataset_with_testcases_strategy())
async def test_evaluation_executes_all_test_cases(dataset: Dataset):
    """
    Property 9: Evaluation executes all test cases.
    
    **Validates: Requirements 3.1, 3.2**
    
    For any dataset and application, initiating an evaluation run should
    execute all test cases in the dataset.
    """
    # Create application profile for the same customer
    profile = ApplicationProfile(
        id="profile_test",
        customer_id=dataset.customer_id,
        name="Test Application",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create mock repository
    mock_repository = AsyncMock()
    mock_repository.get_dataset_by_id.return_value = dataset
    mock_repository.get_application_profile_by_id.return_value = profile
    
    # Mock create_evaluation_run
    created_run = EvaluationRun(
        id="run_test",
        customer_id=dataset.customer_id,
        dataset_id=dataset.id,
        application_profile_id=profile.id,
        status="running",
        start_time=datetime.utcnow(),
        responses=[]
    )
    mock_repository.create_evaluation_run.return_value = created_run
    
    # Track responses added
    responses_added = []
    
    async def mock_add_response(run_id, response):
        responses_added.append(response)
    
    mock_repository.add_response.side_effect = mock_add_response
    
    # Mock update_evaluation_run
    completed_run = EvaluationRun(
        id="run_test",
        customer_id=dataset.customer_id,
        dataset_id=dataset.id,
        application_profile_id=profile.id,
        status="completed",
        start_time=created_run.start_time,
        end_time=datetime.utcnow(),
        responses=[]
    )
    mock_repository.update_evaluation_run.return_value = completed_run
    
    # Create engine
    engine = EvaluationEngine(mock_repository)
    
    # Mock plugin to return successful responses
    with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
        mock_plugin = AsyncMock()
        MockPlugin.return_value = mock_plugin
        
        # Generate responses for each test case
        mock_plugin.send_input.side_effect = [
            ApplicationResponse(
                output=f"Response for {tc.input[:20]}",
                latency=100.0 + i * 10
            )
            for i, tc in enumerate(dataset.test_cases)
        ]
        
        # Execute run
        result = await engine.execute_run(
            dataset.customer_id,
            dataset.id,
            profile.id
        )
        
        # Property: All test cases should be executed
        assert len(responses_added) == len(dataset.test_cases), \
            f"Expected {len(dataset.test_cases)} responses, got {len(responses_added)}"
        
        # Property: Each test case should have exactly one response
        test_case_ids = {tc.id for tc in dataset.test_cases}
        response_test_case_ids = {r.test_case_id for r in responses_added}
        
        assert test_case_ids == response_test_case_ids, \
            f"Test case IDs mismatch: expected {test_case_ids}, got {response_test_case_ids}"
        
        # Property: Plugin send_input should be called for each test case
        assert mock_plugin.send_input.call_count == len(dataset.test_cases), \
            f"Plugin send_input called {mock_plugin.send_input.call_count} times, expected {len(dataset.test_cases)}"
        
        # Property: Each test case input should be sent to the plugin
        sent_inputs = [call[0][0] for call in mock_plugin.send_input.call_args_list]
        expected_inputs = [tc.input for tc in dataset.test_cases]
        
        assert sent_inputs == expected_inputs, \
            f"Inputs sent to plugin don't match test case inputs"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    dataset=dataset_with_testcases_strategy(),
    data=st.data()
)
async def test_response_metadata_completeness(dataset: Dataset, data):
    """
    Property 10: Response metadata completeness.
    
    **Validates: Requirements 3.3, 3.4**
    
    For any captured response, it should include a timestamp, latency measurement,
    and either output or error.
    """
    # Create application profile
    profile = ApplicationProfile(
        id="profile_test",
        customer_id=dataset.customer_id,
        name="Test Application",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create mock repository
    mock_repository = AsyncMock()
    mock_repository.get_dataset_by_id.return_value = dataset
    mock_repository.get_application_profile_by_id.return_value = profile
    
    # Mock create_evaluation_run
    created_run = EvaluationRun(
        id="run_test",
        customer_id=dataset.customer_id,
        dataset_id=dataset.id,
        application_profile_id=profile.id,
        status="running",
        start_time=datetime.utcnow(),
        responses=[]
    )
    mock_repository.create_evaluation_run.return_value = created_run
    
    # Track responses added
    responses_added = []
    
    async def mock_add_response(run_id, response):
        responses_added.append(response)
    
    mock_repository.add_response.side_effect = mock_add_response
    
    # Mock update_evaluation_run
    completed_run = EvaluationRun(
        id="run_test",
        customer_id=dataset.customer_id,
        dataset_id=dataset.id,
        application_profile_id=profile.id,
        status="completed",
        start_time=created_run.start_time,
        end_time=datetime.utcnow(),
        responses=[]
    )
    mock_repository.update_evaluation_run.return_value = completed_run
    
    # Create engine
    engine = EvaluationEngine(mock_repository)
    
    # Mock plugin with mix of successful and failed responses
    with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
        mock_plugin = AsyncMock()
        MockPlugin.return_value = mock_plugin
        
        # Generate mix of successful and failed responses
        responses = []
        for i, tc in enumerate(dataset.test_cases):
            # Randomly decide if this response should have an error
            has_error = data.draw(st.booleans())
            
            if has_error:
                responses.append(ApplicationResponse(
                    output="",
                    latency=data.draw(st.floats(min_value=0.1, max_value=1000.0)),
                    error="Connection timeout"
                ))
            else:
                responses.append(ApplicationResponse(
                    output=f"Response {i}",
                    latency=data.draw(st.floats(min_value=0.1, max_value=1000.0))
                ))
        
        mock_plugin.send_input.side_effect = responses
        
        # Execute run
        result = await engine.execute_run(
            dataset.customer_id,
            dataset.id,
            profile.id
        )
        
        # Property: All responses should have complete metadata
        for response in responses_added:
            # Property: Response must have a timestamp
            assert response.timestamp is not None, \
                f"Response for test case {response.test_case_id} missing timestamp"
            
            assert isinstance(response.timestamp, datetime), \
                f"Response timestamp should be datetime, got {type(response.timestamp)}"
            
            # Property: Response must have latency measurement
            assert response.latency is not None, \
                f"Response for test case {response.test_case_id} missing latency"
            
            assert isinstance(response.latency, (int, float)), \
                f"Response latency should be numeric, got {type(response.latency)}"
            
            assert response.latency >= 0, \
                f"Response latency should be non-negative, got {response.latency}"
            
            # Property: Response must have either output or error (or both)
            has_output = response.output is not None and response.output != ""
            has_error = response.error is not None and response.error != ""
            
            assert has_output or has_error, \
                f"Response for test case {response.test_case_id} has neither output nor error"
            
            # Property: Response must have test_case_id
            assert response.test_case_id is not None, \
                f"Response missing test_case_id"
            
            # Property: Response must have input
            assert response.input is not None and response.input != "", \
                f"Response for test case {response.test_case_id} missing input"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    dataset=dataset_with_testcases_strategy(),
    data=st.data()
)
async def test_partial_failure_resilience(dataset: Dataset, data):
    """
    Property 11: Partial failure resilience.
    
    **Validates: Requirements 3.5, 7.3**
    
    For any evaluation run where some test cases fail, the platform should
    execute all remaining test cases and record which ones failed.
    """
    # Ensure we have at least 2 test cases for meaningful partial failure
    if len(dataset.test_cases) < 2:
        # Add another test case
        dataset.test_cases.append(TestCase(
            id=f"{dataset.id}_tc_extra",
            input="Extra test case",
            expected_output="Extra output"
        ))
    
    # Create application profile
    profile = ApplicationProfile(
        id="profile_test",
        customer_id=dataset.customer_id,
        name="Test Application",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create mock repository
    mock_repository = AsyncMock()
    mock_repository.get_dataset_by_id.return_value = dataset
    mock_repository.get_application_profile_by_id.return_value = profile
    
    # Mock create_evaluation_run
    created_run = EvaluationRun(
        id="run_test",
        customer_id=dataset.customer_id,
        dataset_id=dataset.id,
        application_profile_id=profile.id,
        status="running",
        start_time=datetime.utcnow(),
        responses=[]
    )
    mock_repository.create_evaluation_run.return_value = created_run
    
    # Track responses added
    responses_added = []
    
    async def mock_add_response(run_id, response):
        responses_added.append(response)
    
    mock_repository.add_response.side_effect = mock_add_response
    
    # Mock update_evaluation_run
    completed_run = EvaluationRun(
        id="run_test",
        customer_id=dataset.customer_id,
        dataset_id=dataset.id,
        application_profile_id=profile.id,
        status="completed",
        start_time=created_run.start_time,
        end_time=datetime.utcnow(),
        responses=[]
    )
    mock_repository.update_evaluation_run.return_value = completed_run
    
    # Create engine
    engine = EvaluationEngine(mock_repository)
    
    # Mock plugin with mix of successful and failed responses
    # Ensure at least one failure and one success
    with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
        mock_plugin = AsyncMock()
        MockPlugin.return_value = mock_plugin
        
        # Generate responses with at least one failure
        responses = []
        failure_indices = set()
        
        # Ensure at least one failure
        failure_index = data.draw(st.integers(min_value=0, max_value=len(dataset.test_cases) - 1))
        failure_indices.add(failure_index)
        
        # Randomly add more failures
        for i in range(len(dataset.test_cases)):
            if i == failure_index or (i != 0 and data.draw(st.booleans(), label=f"fail_{i}")):
                failure_indices.add(i)
        
        # Ensure at least one success
        if len(failure_indices) == len(dataset.test_cases):
            # Remove one failure to ensure at least one success
            failure_indices.remove(0)
        
        for i, tc in enumerate(dataset.test_cases):
            if i in failure_indices:
                responses.append(ApplicationResponse(
                    output="",
                    latency=data.draw(st.floats(min_value=0.1, max_value=1000.0)),
                    error=data.draw(st.sampled_from([
                        "Connection timeout",
                        "HTTP 500 Internal Server Error",
                        "Application unavailable"
                    ]))
                ))
            else:
                responses.append(ApplicationResponse(
                    output=f"Success response {i}",
                    latency=data.draw(st.floats(min_value=0.1, max_value=1000.0))
                ))
        
        mock_plugin.send_input.side_effect = responses
        
        # Execute run
        result = await engine.execute_run(
            dataset.customer_id,
            dataset.id,
            profile.id
        )
        
        # Property: All test cases should be executed despite failures
        assert len(responses_added) == len(dataset.test_cases), \
            f"Expected {len(dataset.test_cases)} responses despite failures, got {len(responses_added)}"
        
        # Property: Failed test cases should be recorded with error messages
        failed_responses = [r for r in responses_added if r.error]
        assert len(failed_responses) == len(failure_indices), \
            f"Expected {len(failure_indices)} failed responses, got {len(failed_responses)}"
        
        # Property: Successful test cases should have output
        successful_responses = [r for r in responses_added if not r.error]
        assert len(successful_responses) == len(dataset.test_cases) - len(failure_indices), \
            f"Expected {len(dataset.test_cases) - len(failure_indices)} successful responses"
        
        for response in successful_responses:
            assert response.output is not None and response.output != "", \
                f"Successful response for {response.test_case_id} should have output"
        
        # Property: Run should be marked as completed (not failed)
        assert result.status == "completed", \
            f"Run should be completed despite partial failures, got status: {result.status}"
        
        # Property: All test case IDs should be present in responses
        test_case_ids = {tc.id for tc in dataset.test_cases}
        response_test_case_ids = {r.test_case_id for r in responses_added}
        
        assert test_case_ids == response_test_case_ids, \
            f"All test cases should have responses despite failures"



@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    dataset=dataset_with_testcases_strategy(),
    data=st.data()
)
async def test_metrics_calculation_completeness(dataset: Dataset, data):
    """
    Property 14: Metrics calculation completeness.
    
    **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
    
    For any completed evaluation run, all responses should have calculated metrics
    including accuracy (when expected output exists), relevance, and latency.
    """
    # Create responses with mix of expected outputs
    responses = []
    
    for i, tc in enumerate(dataset.test_cases):
        # Generate response output
        output = data.draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
        )))
        
        # Generate latency
        latency = data.draw(st.floats(min_value=0.1, max_value=5000.0))
        
        # Create response (only successful responses for metrics calculation)
        response = Response(
            test_case_id=tc.id,
            input=tc.input,
            output=output.strip() or "test output",
            latency=latency,
            timestamp=datetime.utcnow(),
            error=None
        )
        responses.append(response)
    
    # Create metrics calculator
    calculator = MetricsCalculator()
    
    # Calculate individual metrics for each response
    for i, (response, tc) in enumerate(zip(responses, dataset.test_cases)):
        metrics = calculator.calculate_individual_metrics(response, tc.expected_output)
        
        # Property: Metrics should always be calculated
        assert metrics is not None, \
            f"Metrics should be calculated for response {i}"
        
        # Property: Relevance should always be calculated
        assert metrics.relevance is not None, \
            f"Relevance should be calculated for response {i}"
        
        assert isinstance(metrics.relevance, (int, float)), \
            f"Relevance should be numeric, got {type(metrics.relevance)}"
        
        assert 0.0 <= metrics.relevance <= 1.0, \
            f"Relevance should be between 0 and 1, got {metrics.relevance}"
        
        # Property: Accuracy should be calculated when expected output exists
        if tc.expected_output is not None:
            assert metrics.accuracy is not None, \
                f"Accuracy should be calculated when expected output exists for response {i}"
            
            assert isinstance(metrics.accuracy, (int, float)), \
                f"Accuracy should be numeric, got {type(metrics.accuracy)}"
            
            assert 0.0 <= metrics.accuracy <= 1.0, \
                f"Accuracy should be between 0 and 1, got {metrics.accuracy}"
        else:
            # Property: Accuracy should be None when no expected output
            assert metrics.accuracy is None, \
                f"Accuracy should be None when no expected output for response {i}"
        
        # Property: Latency should be present in response
        assert response.latency is not None, \
            f"Latency should be present for response {i}"
        
        assert isinstance(response.latency, (int, float)), \
            f"Latency should be numeric, got {type(response.latency)}"
        
        assert response.latency >= 0, \
            f"Latency should be non-negative, got {response.latency}"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    dataset=dataset_with_testcases_strategy(),
    data=st.data()
)
async def test_metrics_aggregation_correctness(dataset: Dataset, data):
    """
    Property 15: Metrics aggregation correctness.
    
    **Validates: Requirements 4.6**
    
    For any evaluation run, the aggregated run-level metrics should be correctly
    calculated from individual response metrics (e.g., average latency equals
    sum of latencies divided by count).
    """
    # Create responses with known values for verification
    responses = []
    latencies = []
    accuracy_scores = []
    relevance_scores = []
    
    for i, tc in enumerate(dataset.test_cases):
        # Generate response output
        output = data.draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), whitelist_characters=' \n'
        )))
        
        # Generate latency
        latency = data.draw(st.floats(min_value=0.1, max_value=5000.0))
        latencies.append(latency)
        
        # Create response (only successful responses)
        response = Response(
            test_case_id=tc.id,
            input=tc.input,
            output=output.strip() or "test output",
            latency=latency,
            timestamp=datetime.utcnow(),
            error=None
        )
        responses.append(response)
    
    # Create metrics calculator
    calculator = MetricsCalculator()
    
    # Calculate individual metrics to get expected values
    for response, tc in zip(responses, dataset.test_cases):
        # Calculate accuracy if expected output exists
        if tc.expected_output is not None:
            accuracy = calculator.calculate_accuracy(response.output, tc.expected_output)
            if accuracy is not None:
                accuracy_scores.append(accuracy)
        
        # Calculate relevance
        relevance = calculator.calculate_relevance(response.input, response.output)
        relevance_scores.append(relevance)
    
    # Aggregate metrics
    aggregated = calculator.aggregate_metrics(responses, dataset.test_cases)
    
    # Property: Total test cases should match response count
    assert aggregated.total_test_cases == len(responses), \
        f"Total test cases should be {len(responses)}, got {aggregated.total_test_cases}"
    
    # Property: Failed test cases should be 0 (all successful)
    assert aggregated.failed_test_cases == 0, \
        f"Failed test cases should be 0, got {aggregated.failed_test_cases}"
    
    # Property: Success rate should be 1.0 (all successful)
    assert aggregated.success_rate == 1.0, \
        f"Success rate should be 1.0, got {aggregated.success_rate}"
    
    # Property: Average latency should equal mean of latencies
    import statistics
    expected_avg_latency = statistics.mean(latencies)
    assert abs(aggregated.average_latency - expected_avg_latency) < 0.01, \
        f"Average latency should be {expected_avg_latency}, got {aggregated.average_latency}"
    
    # Property: Median latency should equal median of latencies
    expected_median_latency = statistics.median(latencies)
    assert abs(aggregated.median_latency - expected_median_latency) < 0.01, \
        f"Median latency should be {expected_median_latency}, got {aggregated.median_latency}"
    
    # Property: P95 latency should be at or above 95% of latencies
    sorted_latencies = sorted(latencies)
    p95_index = int(len(sorted_latencies) * 0.95)
    expected_p95 = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]
    assert abs(aggregated.p95_latency - expected_p95) < 0.01, \
        f"P95 latency should be {expected_p95}, got {aggregated.p95_latency}"
    
    # Property: Average accuracy should equal mean of accuracy scores (if any)
    if accuracy_scores:
        expected_avg_accuracy = statistics.mean(accuracy_scores)
        assert abs(aggregated.average_accuracy - expected_avg_accuracy) < 0.01, \
            f"Average accuracy should be {expected_avg_accuracy}, got {aggregated.average_accuracy}"
    else:
        # If no accuracy scores, average should be 0.0
        assert aggregated.average_accuracy == 0.0, \
            f"Average accuracy should be 0.0 when no expected outputs, got {aggregated.average_accuracy}"
    
    # Property: Average relevance should equal mean of relevance scores
    if relevance_scores:
        expected_avg_relevance = statistics.mean(relevance_scores)
        assert abs(aggregated.average_relevance - expected_avg_relevance) < 0.01, \
            f"Average relevance should be {expected_avg_relevance}, got {aggregated.average_relevance}"
    
    # Property: All aggregated values should be non-negative
    assert aggregated.average_accuracy >= 0, "Average accuracy should be non-negative"
    assert aggregated.average_relevance >= 0, "Average relevance should be non-negative"
    assert aggregated.average_latency >= 0, "Average latency should be non-negative"
    assert aggregated.median_latency >= 0, "Median latency should be non-negative"
    assert aggregated.p95_latency >= 0, "P95 latency should be non-negative"
    
    # Property: Accuracy and relevance should be in [0, 1] range
    assert 0 <= aggregated.average_accuracy <= 1, \
        f"Average accuracy should be in [0, 1], got {aggregated.average_accuracy}"
    assert 0 <= aggregated.average_relevance <= 1, \
        f"Average relevance should be in [0, 1], got {aggregated.average_relevance}"
    
    # Property: Success rate should be in [0, 1] range
    assert 0 <= aggregated.success_rate <= 1, \
        f"Success rate should be in [0, 1], got {aggregated.success_rate}"
