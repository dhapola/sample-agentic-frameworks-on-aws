"""Evaluation run model for test execution records."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .metrics import AggregatedMetrics
from .response import Response


# Valid evaluation run statuses
EvaluationStatus = Literal["pending", "running", "completed", "failed"]


class EvaluationRun(BaseModel):
    """
    Evaluation run execution record.
    
    Represents an execution of a dataset against an application profile,
    including all responses and calculated metrics.
    Scoped to a customer for tenant isolation.
    """
    
    id: str = Field(..., description="Unique evaluation run identifier")
    customer_id: str = Field(..., description="Customer ID for tenant isolation")
    dataset_id: str = Field(..., description="ID of the dataset being evaluated")
    application_profile_id: str = Field(..., description="ID of the application profile being tested")
    status: EvaluationStatus = Field(
        default="pending",
        description="Current status of the evaluation run"
    )
    start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the evaluation run started"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="When the evaluation run completed"
    )
    responses: List[Response] = Field(
        default_factory=list,
        description="List of responses from the application"
    )
    metrics: Optional[AggregatedMetrics] = Field(
        default=None,
        description="Aggregated metrics for the run"
    )
    
    @field_validator('customer_id', 'dataset_id', 'application_profile_id')
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate IDs are not empty."""
        if not v or not v.strip():
            raise ValueError("ID fields cannot be empty")
        return v.strip()
    
    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate end_time is after start_time if both are set."""
        if v is not None and 'start_time' in info.data:
            start_time = info.data['start_time']
            if v < start_time:
                raise ValueError("End time cannot be before start time")
        return v
    
    @field_validator('responses')
    @classmethod
    def validate_responses(cls, v: List[Response]) -> List[Response]:
        """Validate responses list."""
        # Ensure response test_case_ids are unique within the run
        if v:
            test_case_ids = [r.test_case_id for r in v]
            if len(test_case_ids) != len(set(test_case_ids)):
                raise ValueError("Response test case IDs must be unique within a run")
        return v
    
    @field_validator('metrics')
    @classmethod
    def validate_metrics(cls, v: Optional[AggregatedMetrics], info) -> Optional[AggregatedMetrics]:
        """Validate metrics consistency with responses."""
        if v is not None and 'responses' in info.data:
            responses = info.data['responses']
            if v.total_test_cases != len(responses):
                raise ValueError(
                    f"Metrics total_test_cases ({v.total_test_cases}) "
                    f"must match number of responses ({len(responses)})"
                )
            if v.failed_test_cases > v.total_test_cases:
                raise ValueError(
                    f"Failed test cases ({v.failed_test_cases}) "
                    f"cannot exceed total test cases ({v.total_test_cases})"
                )
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "run_123",
                "customer_id": "cust_123456",
                "dataset_id": "dataset_123",
                "application_profile_id": "app_profile_123",
                "status": "completed",
                "start_time": "2024-01-01T12:00:00Z",
                "end_time": "2024-01-01T12:05:00Z",
                "responses": [
                    {
                        "test_case_id": "tc_001",
                        "input": "What is the capital of France?",
                        "output": "The capital of France is Paris.",
                        "latency": 245.5,
                        "timestamp": "2024-01-01T12:00:00Z",
                        "individual_metrics": {
                            "accuracy": 0.95,
                            "relevance": 0.88
                        }
                    }
                ],
                "metrics": {
                    "average_accuracy": 0.92,
                    "average_relevance": 0.87,
                    "average_latency": 245.5,
                    "median_latency": 230.0,
                    "p95_latency": 380.0,
                    "success_rate": 0.98,
                    "total_test_cases": 100,
                    "failed_test_cases": 2
                }
            }
        }
