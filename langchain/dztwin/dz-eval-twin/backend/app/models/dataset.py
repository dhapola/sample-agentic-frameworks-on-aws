"""Dataset model for test case collections."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator

from .test_case import TestCase


class Dataset(BaseModel):
    """
    Collection of test cases for evaluation.
    
    Represents a dataset containing multiple test cases used to
    systematically evaluate a generative AI application.
    Scoped to a customer for tenant isolation.
    """
    
    id: str = Field(..., description="Unique dataset identifier")
    customer_id: str = Field(..., description="Customer ID for tenant isolation")
    name: str = Field(..., min_length=1, max_length=200, description="Dataset name")
    description: str = Field(..., max_length=1000, description="Dataset description")
    test_cases: List[TestCase] = Field(
        default_factory=list,
        description="List of test cases in the dataset"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dataset name is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Dataset name cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator('customer_id')
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id is not empty."""
        if not v or not v.strip():
            raise ValueError("Customer ID cannot be empty")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description."""
        # Allow empty description but strip whitespace
        return v.strip() if v else ""
    
    @field_validator('test_cases')
    @classmethod
    def validate_test_cases(cls, v: List[TestCase]) -> List[TestCase]:
        """Validate test cases list."""
        # Ensure test case IDs are unique within the dataset
        if v:
            ids = [tc.id for tc in v]
            if len(ids) != len(set(ids)):
                raise ValueError("Test case IDs must be unique within a dataset")
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "dataset_123",
                "customer_id": "cust_123456",
                "name": "Geography Questions",
                "description": "Test cases for geography knowledge",
                "test_cases": [
                    {
                        "id": "tc_001",
                        "input": "What is the capital of France?",
                        "expected_output": "Paris",
                        "metadata": {"category": "geography"}
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
