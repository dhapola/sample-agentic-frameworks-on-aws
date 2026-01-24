"""Test case model for evaluation datasets."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TestCase(BaseModel):
    """
    Individual test case within a dataset.
    
    Represents a single input-output pair used for evaluating
    a generative AI application.
    """
    
    id: str = Field(..., description="Unique test case identifier")
    input: str = Field(..., min_length=1, description="Input text for the gen AI application")
    expected_output: Optional[str] = Field(
        default=None,
        description="Expected output for accuracy comparison (optional)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about the test case"
    )
    
    @field_validator('input')
    @classmethod
    def validate_input(cls, v: str) -> str:
        """Validate input is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Test case input cannot be empty or whitespace only")
        return v
    
    @field_validator('expected_output')
    @classmethod
    def validate_expected_output(cls, v: Optional[str]) -> Optional[str]:
        """Validate expected output if provided."""
        if v is not None and isinstance(v, str):
            # Allow empty string as valid expected output
            return v
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "tc_001",
                "input": "What is the capital of France?",
                "expected_output": "Paris",
                "metadata": {
                    "category": "geography",
                    "difficulty": "easy"
                }
            }
        }
