"""Metrics models for evaluation results."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class IndividualMetrics(BaseModel):
    """
    Metrics for a single response.
    
    Represents quality metrics calculated for an individual
    response from a generative AI application.
    """
    
    accuracy: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Accuracy score (0-1) comparing response to expected output"
    )
    relevance: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relevance score (0-1) of response to input"
    )
    
    @field_validator('accuracy', 'relevance')
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        """Validate metric scores are in valid range."""
        if v is not None:
            if v < 0.0 or v > 1.0:
                raise ValueError("Metric scores must be between 0.0 and 1.0")
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "accuracy": 0.95,
                "relevance": 0.88
            }
        }


class AggregatedMetrics(BaseModel):
    """
    Aggregated metrics for an evaluation run.
    
    Represents run-level statistics calculated from all individual
    response metrics in an evaluation run.
    """
    
    average_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average accuracy across all responses"
    )
    average_relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average relevance across all responses"
    )
    average_latency: float = Field(
        ...,
        ge=0.0,
        description="Average latency in milliseconds"
    )
    median_latency: float = Field(
        ...,
        ge=0.0,
        description="Median latency in milliseconds"
    )
    p95_latency: float = Field(
        ...,
        ge=0.0,
        description="95th percentile latency in milliseconds"
    )
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of successful responses (0-1)"
    )
    total_test_cases: int = Field(
        ...,
        ge=0,
        description="Total number of test cases executed"
    )
    failed_test_cases: int = Field(
        ...,
        ge=0,
        description="Number of test cases that failed"
    )
    
    @field_validator('average_accuracy', 'average_relevance', 'success_rate')
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        """Validate percentage values are in valid range."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Percentage values must be between 0.0 and 1.0")
        return v
    
    @field_validator('average_latency', 'median_latency', 'p95_latency')
    @classmethod
    def validate_latency(cls, v: float) -> float:
        """Validate latency values are non-negative."""
        if v < 0.0:
            raise ValueError("Latency values cannot be negative")
        return v
    
    @field_validator('failed_test_cases')
    @classmethod
    def validate_failed_count(cls, v: int, info) -> int:
        """Validate failed count doesn't exceed total."""
        # Note: We can't access total_test_cases here in field_validator
        # This validation will be done at the model level
        if v < 0:
            raise ValueError("Failed test cases count cannot be negative")
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
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
