"""Evaluation execution API endpoints (tenant-scoped)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.engine.evaluation_engine import EvaluationEngine
from app.engine.metrics_calculator import MetricsCalculator
from app.middleware.error_handler import NotFoundError, ValidationError, UnauthorizedError
from app.models.evaluation_run import EvaluationRun
from app.models.metrics import AggregatedMetrics, IndividualMetrics
from app.models.response import Response
from app.utils.validation import (
    validate_dataset_id,
    validate_application_profile_id,
    validate_evaluation_run_id,
    validate_list_not_empty
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


# Request/Response models
class StartEvaluationRequest(BaseModel):
    """Request model for starting an evaluation run."""
    
    dataset_id: str = Field(..., alias="datasetId", description="ID of the dataset to evaluate")
    application_profile_id: str = Field(..., alias="applicationProfileId", description="ID of the application profile to test")
    
    class Config:
        populate_by_name = True  # Accept both snake_case and camelCase
        json_schema_extra = {
            "example": {
                "datasetId": "ds_abc123",
                "applicationProfileId": "prof_xyz789"
            }
        }


class CompareRunsRequest(BaseModel):
    """Request model for comparing multiple evaluation runs."""
    
    run_ids: List[str] = Field(..., alias="runIds", min_length=2, description="List of evaluation run IDs to compare")
    
    class Config:
        populate_by_name = True  # Accept both snake_case and camelCase
        json_schema_extra = {
            "example": {
                "runIds": ["run_abc123", "run_def456", "run_ghi789"]
            }
        }


class IndividualMetricsResponse(BaseModel):
    """Response model for individual metrics."""
    
    accuracy: Optional[float] = None
    relevance: Optional[float] = None
    
    @classmethod
    def from_metrics(cls, metrics: Optional[IndividualMetrics]) -> Optional["IndividualMetricsResponse"]:
        """Convert IndividualMetrics model to response."""
        if metrics is None:
            return None
        return cls(
            accuracy=metrics.accuracy,
            relevance=metrics.relevance
        )


class ResponseResponse(BaseModel):
    """Response model for evaluation response data."""
    
    test_case_id: str = Field(..., alias="testCaseId")
    input: str
    output: str
    latency: float
    timestamp: str
    error: Optional[str] = None
    individual_metrics: Optional[IndividualMetricsResponse] = Field(None, alias="individualMetrics")
    
    class Config:
        populate_by_name = True
        by_alias = True  # Serialize using aliases (camelCase)
    
    @classmethod
    def from_response(cls, response: Response) -> "ResponseResponse":
        """Convert Response model to response."""
        return cls(
            test_case_id=response.test_case_id,
            input=response.input,
            output=response.output,
            latency=response.latency,
            timestamp=response.timestamp.isoformat(),
            error=response.error,
            individual_metrics=IndividualMetricsResponse.from_metrics(response.individual_metrics)
        )


class AggregatedMetricsResponse(BaseModel):
    """Response model for aggregated metrics."""
    
    average_accuracy: float = Field(..., alias="averageAccuracy")
    average_relevance: float = Field(..., alias="averageRelevance")
    average_latency: float = Field(..., alias="averageLatency")
    median_latency: float = Field(..., alias="medianLatency")
    p95_latency: float = Field(..., alias="p95Latency")
    success_rate: float = Field(..., alias="successRate")
    total_test_cases: int = Field(..., alias="totalTestCases")
    failed_test_cases: int = Field(..., alias="failedTestCases")
    
    class Config:
        populate_by_name = True
        by_alias = True  # Serialize using aliases (camelCase)
    
    @classmethod
    def from_metrics(cls, metrics: Optional[AggregatedMetrics]) -> Optional["AggregatedMetricsResponse"]:
        """Convert AggregatedMetrics model to response."""
        if metrics is None:
            return None
        return cls(
            average_accuracy=metrics.average_accuracy,
            average_relevance=metrics.average_relevance,
            average_latency=metrics.average_latency,
            median_latency=metrics.median_latency,
            p95_latency=metrics.p95_latency,
            success_rate=metrics.success_rate,
            total_test_cases=metrics.total_test_cases,
            failed_test_cases=metrics.failed_test_cases
        )


class EvaluationRunResponse(BaseModel):
    """Response model for evaluation run data."""
    
    id: str
    customer_id: str = Field(..., alias="customerId")
    dataset_id: str = Field(..., alias="datasetId")
    application_profile_id: str = Field(..., alias="applicationProfileId")
    status: str
    start_time: str = Field(..., alias="startTime")
    end_time: Optional[str] = Field(None, alias="endTime")
    responses: List[ResponseResponse]
    metrics: Optional[AggregatedMetricsResponse] = None
    
    class Config:
        populate_by_name = True
        by_alias = True  # Serialize using aliases (camelCase)
    
    @classmethod
    def from_evaluation_run(cls, run: EvaluationRun) -> "EvaluationRunResponse":
        """Convert EvaluationRun model to response."""
        return cls(
            id=run.id,
            customer_id=run.customer_id,
            dataset_id=run.dataset_id,
            application_profile_id=run.application_profile_id,
            status=run.status,
            start_time=run.start_time.isoformat(),
            end_time=run.end_time.isoformat() if run.end_time else None,
            responses=[ResponseResponse.from_response(r) for r in run.responses],
            metrics=AggregatedMetricsResponse.from_metrics(run.metrics)
        )


class EvaluationRunSummaryResponse(BaseModel):
    """Response model for evaluation run summary (without full responses)."""
    
    id: str
    customer_id: str = Field(..., alias="customerId")
    dataset_id: str = Field(..., alias="datasetId")
    application_profile_id: str = Field(..., alias="applicationProfileId")
    status: str
    start_time: str = Field(..., alias="startTime")
    end_time: Optional[str] = Field(None, alias="endTime")
    metrics: Optional[AggregatedMetricsResponse] = None
    
    class Config:
        populate_by_name = True
        by_alias = True  # Serialize using aliases (camelCase)
    
    @classmethod
    def from_evaluation_run(cls, run: EvaluationRun) -> "EvaluationRunSummaryResponse":
        """Convert EvaluationRun model to summary response."""
        return cls(
            id=run.id,
            customer_id=run.customer_id,
            dataset_id=run.dataset_id,
            application_profile_id=run.application_profile_id,
            status=run.status,
            start_time=run.start_time.isoformat(),
            end_time=run.end_time.isoformat() if run.end_time else None,
            metrics=AggregatedMetricsResponse.from_metrics(run.metrics)
        )


class ComparisonMetrics(BaseModel):
    """Metrics for a single run in comparison."""
    
    run_id: str = Field(..., alias="runId")
    dataset_id: str = Field(..., alias="datasetId")
    application_profile_id: str = Field(..., alias="applicationProfileId")
    start_time: str = Field(..., alias="startTime")
    metrics: Optional[AggregatedMetricsResponse] = None
    
    class Config:
        populate_by_name = True
        by_alias = True  # Serialize using aliases (camelCase)


class CompareRunsResponse(BaseModel):
    """Response model for run comparison."""
    
    runs: List[ComparisonMetrics]
    
    class Config:
        json_schema_extra = {
            "example": {
                "runs": [
                    {
                        "run_id": "run_abc123",
                        "dataset_id": "ds_abc123",
                        "application_profile_id": "prof_xyz789",
                        "start_time": "2024-01-15T10:30:00",
                        "metrics": {
                            "average_accuracy": 0.85,
                            "average_relevance": 0.92,
                            "average_latency": 250.5,
                            "median_latency": 230.0,
                            "p95_latency": 450.0,
                            "success_rate": 0.95,
                            "total_test_cases": 20,
                            "failed_test_cases": 1
                        }
                    }
                ]
            }
        }


# Dependency to get evaluation engine
def get_evaluation_engine() -> EvaluationEngine:
    """Get evaluation engine instance."""
    repository = DataRepository(database_manager.database)
    return EvaluationEngine(repository)


# Dependency to get metrics calculator
def get_metrics_calculator() -> MetricsCalculator:
    """Get metrics calculator instance."""
    return MetricsCalculator()


# Dependency to get repository
def get_repository() -> DataRepository:
    """Get data repository instance."""
    return DataRepository(database_manager.database)


# Dependency to get customer_id from request state
def get_customer_id(request: Request) -> str:
    """
    Get customer_id from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Customer ID from request state
        
    Raises:
        UnauthorizedError: If customer_id not found in request state
    """
    customer_id = getattr(request.state, "customer_id", None)
    if not customer_id:
        raise UnauthorizedError("Customer context required. Please provide X-Customer-ID header.")
    return customer_id


@router.post(
    "",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start evaluation run",
    description="Start a new evaluation run for a dataset against an application profile"
)
async def start_evaluation_run(
    request_data: StartEvaluationRequest,
    customer_id: str = Depends(get_customer_id),
    engine: EvaluationEngine = Depends(get_evaluation_engine),
    calculator: MetricsCalculator = Depends(get_metrics_calculator),
    repository: DataRepository = Depends(get_repository)
) -> EvaluationRunResponse:
    """
    Start a new evaluation run.
    
    This endpoint:
    1. Validates that the dataset and application profile belong to the customer
    2. Executes all test cases in the dataset against the application
    3. Captures responses with timestamps and latency measurements
    4. Calculates individual and aggregated metrics
    5. Returns the completed evaluation run with all results
    
    Args:
        request_data: Evaluation run request
        customer_id: Customer ID from request context
        engine: Evaluation engine instance
        calculator: Metrics calculator instance
        repository: Data repository instance
        
    Returns:
        Created evaluation run with responses and metrics
        
    Raises:
        ValidationError: If validation fails
        NotFoundError: If dataset or application profile not found
        UnauthorizedError: If customer context missing
    """
    try:
        # Validate IDs format
        validated_dataset_id = validate_dataset_id(request_data.dataset_id)
        validated_profile_id = validate_application_profile_id(request_data.application_profile_id)
        
        # Execute the evaluation run
        run = await engine.execute_run(
            customer_id=customer_id,
            dataset_id=validated_dataset_id,
            application_profile_id=validated_profile_id
        )
        
        # Calculate metrics if run completed successfully
        if run.status == "completed" and run.responses:
            # Get dataset to access test cases for expected outputs
            dataset = await repository.get_dataset_by_id(
                validated_dataset_id,
                customer_id
            )
            
            if dataset:
                # Calculate individual metrics for each response
                for response in run.responses:
                    # Find the corresponding test case
                    test_case = next(
                        (tc for tc in dataset.test_cases if tc.id == response.test_case_id),
                        None
                    )
                    
                    if test_case and not response.error:
                        response.individual_metrics = calculator.calculate_individual_metrics(
                            response,
                            test_case.expected_output
                        )
                
                # Calculate aggregated metrics
                aggregated_metrics = calculator.aggregate_metrics(
                    run.responses,
                    dataset.test_cases
                )
                
                # Update run with metrics
                await repository.update_evaluation_run(
                    run.id,
                    customer_id,
                    {
                        "metrics": aggregated_metrics.model_dump(),
                        "responses": [r.model_dump() for r in run.responses]
                    }
                )
                
                # Update local run object
                run.metrics = aggregated_metrics
        
        return EvaluationRunResponse.from_evaluation_run(run)
        
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))
    except ConnectionError as e:
        raise ValidationError(f"Failed to connect to application: {str(e)}")
    except Exception as e:
        logger.error(f"Error starting evaluation run: {e}")
        raise ValidationError(f"Failed to start evaluation run: {str(e)}")


@router.get(
    "",
    response_model=List[EvaluationRunSummaryResponse],
    summary="List evaluation runs",
    description="Get all evaluation runs for the authenticated customer"
)
async def list_evaluation_runs(
    customer_id: str = Depends(get_customer_id),
    repository: DataRepository = Depends(get_repository)
) -> List[EvaluationRunSummaryResponse]:
    """
    Get all evaluation runs for a customer.
    
    Returns a summary of each run without the full response details
    to keep the response size manageable.
    
    Args:
        customer_id: Customer ID from request context
        repository: Data repository instance
        
    Returns:
        List of evaluation run summaries for the customer
        
    Raises:
        UnauthorizedError: If customer context missing
    """
    try:
        runs = await repository.get_evaluation_runs(customer_id)
        return [EvaluationRunSummaryResponse.from_evaluation_run(r) for r in runs]
    except Exception as e:
        logger.error(f"Error listing evaluation runs: {e}")
        raise ValidationError(f"Failed to list evaluation runs: {str(e)}")


@router.get(
    "/{run_id}",
    response_model=EvaluationRunResponse,
    summary="Get evaluation run details",
    description="Get detailed results of a specific evaluation run"
)
async def get_evaluation_run(
    run_id: str,
    customer_id: str = Depends(get_customer_id),
    repository: DataRepository = Depends(get_repository)
) -> EvaluationRunResponse:
    """
    Get evaluation run by ID with full details.
    
    Returns the complete evaluation run including all responses,
    individual metrics, and aggregated metrics.
    
    Args:
        run_id: Evaluation run ID
        customer_id: Customer ID from request context
        repository: Data repository instance
        
    Returns:
        Evaluation run details with all responses and metrics
        
    Raises:
        NotFoundError: If evaluation run not found
        UnauthorizedError: If customer context missing
        ValidationError: If run ID is invalid
    """
    try:
        # Validate run_id format
        validated_run_id = validate_evaluation_run_id(run_id)
        
        run = await repository.get_evaluation_run_by_id(validated_run_id, customer_id)
        
        if run is None:
            raise NotFoundError(f"Evaluation run not found: {validated_run_id}")
        
        return EvaluationRunResponse.from_evaluation_run(run)
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation run: {e}")
        raise ValidationError(f"Failed to get evaluation run: {str(e)}")


@router.post(
    "/compare",
    response_model=CompareRunsResponse,
    summary="Compare evaluation runs",
    description="Compare metrics across multiple evaluation runs"
)
async def compare_runs(
    request_data: CompareRunsRequest,
    customer_id: str = Depends(get_customer_id),
    repository: DataRepository = Depends(get_repository)
) -> CompareRunsResponse:
    """
    Compare multiple evaluation runs.
    
    Returns metrics for all specified runs to enable side-by-side comparison.
    All runs must belong to the authenticated customer.
    
    Args:
        request_data: Comparison request with run IDs
        customer_id: Customer ID from request context
        repository: Data repository instance
        
    Returns:
        Comparison data with metrics for all specified runs
        
    Raises:
        ValidationError: If validation fails or runs not found
        UnauthorizedError: If customer context missing
    """
    try:
        # Validate run IDs list
        validate_list_not_empty(request_data.run_ids, "Run IDs", min_items=2)
        
        if len(request_data.run_ids) < 2:
            raise ValidationError("At least 2 run IDs are required for comparison")
        
        comparison_data = []
        
        for run_id in request_data.run_ids:
            # Validate each run_id format
            validated_run_id = validate_evaluation_run_id(run_id)
            
            run = await repository.get_evaluation_run_by_id(validated_run_id, customer_id)
            
            if run is None:
                raise NotFoundError(f"Evaluation run not found: {validated_run_id}")
            
            comparison_data.append(
                ComparisonMetrics(
                    run_id=run.id,
                    dataset_id=run.dataset_id,
                    application_profile_id=run.application_profile_id,
                    start_time=run.start_time.isoformat(),
                    metrics=AggregatedMetricsResponse.from_metrics(run.metrics)
                )
            )
        
        return CompareRunsResponse(runs=comparison_data)
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error comparing runs: {e}")
        raise ValidationError(f"Failed to compare runs: {str(e)}")
