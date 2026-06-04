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
    Linked to an application profile for targeted evaluation.
    """
    
    id: str = Field(..., description="Unique dataset identifier")
    customer_id: str = Field(..., description="Customer ID for tenant isolation")
    application_profile_id: str = Field(..., description="Application profile ID this dataset is designed for")
    name: str = Field(..., min_length=1, max_length=200, description="Dataset name")
    description: str = Field(..., max_length=1000, description="Dataset description")
    file_path: str = Field(..., description="Path to the CSV file containing test cases")
    test_cases: List[TestCase] = Field(
        default_factory=list,
        description="List of test cases in the dataset (parsed from CSV)"
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
    
    @field_validator('customer_id', 'application_profile_id')
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id and application_profile_id are not empty."""
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description."""
        # Allow empty description but strip whitespace
        return v.strip() if v else ""
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file_path is not empty."""
        if not v or not v.strip():
            raise ValueError("File path cannot be empty")
        return v.strip()
    
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
                "application_profile_id": "prof_xyz789",
                "name": "Geography Questions",
                "description": "Test cases for geography knowledge",
                "file_path": "datasets/cust_123456/geography_questions.csv",
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
