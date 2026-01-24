"""Validation utilities for API endpoints."""

import re
from typing import Optional
from urllib.parse import urlparse

from app.middleware.error_handler import ValidationError


def validate_url(url: str, field_name: str = "URL") -> str:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated and stripped URL
        
    Raises:
        ValidationError: If URL is invalid
    """
    if not url:
        raise ValidationError(f"{field_name} is required")
    
    stripped = url.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty or whitespace only")
    
    # Check if URL starts with http:// or https://
    if not stripped.startswith(("http://", "https://")):
        raise ValidationError(f"{field_name} must start with http:// or https://")
    
    # Parse URL to validate structure
    try:
        parsed = urlparse(stripped)
        if not parsed.netloc:
            raise ValidationError(f"{field_name} must have a valid domain")
        
        # Check for reasonable length
        if len(stripped) > 2048:
            raise ValidationError(f"{field_name} is too long (maximum 2048 characters)")
        
        return stripped
    except Exception as e:
        raise ValidationError(f"{field_name} format is invalid: {str(e)}")


def validate_phone_number(phone: Optional[str], field_name: str = "Phone number") -> Optional[str]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated and stripped phone number, or None if not provided
        
    Raises:
        ValidationError: If phone number is invalid
    """
    if phone is None:
        return None
    
    stripped = phone.strip()
    if not stripped:
        return None
    
    # Check for reasonable length (international numbers can be up to 15 digits + formatting)
    if len(stripped) > 30:
        raise ValidationError(f"{field_name} is too long (maximum 30 characters)")
    
    # Must contain at least one digit
    if not any(c.isdigit() for c in stripped):
        raise ValidationError(f"{field_name} must contain at least one digit")
    
    # Check for valid characters (digits, spaces, hyphens, parentheses, plus sign)
    if not re.match(r'^[\d\s\-\(\)\+\.]+$', stripped):
        raise ValidationError(f"{field_name} contains invalid characters")
    
    return stripped


def validate_id_format(id_value: str, field_name: str = "ID") -> str:
    """
    Validate ID format.
    
    Args:
        id_value: ID value to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated and stripped ID
        
    Raises:
        ValidationError: If ID is invalid
    """
    if not id_value:
        raise ValidationError(f"{field_name} is required")
    
    stripped = id_value.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty or whitespace only")
    
    # Check for reasonable length (IDs shouldn't be too long)
    if len(stripped) > 200:
        raise ValidationError(f"{field_name} is too long (maximum 200 characters)")
    
    return stripped


def validate_customer_id(customer_id: Optional[str]) -> str:
    """
    Validate customer ID.
    
    Args:
        customer_id: Customer ID to validate
        
    Returns:
        Validated customer ID
        
    Raises:
        ValidationError: If customer ID is invalid
    """
    return validate_id_format(customer_id, "Customer ID")


def validate_dataset_id(dataset_id: Optional[str]) -> str:
    """
    Validate dataset ID.
    
    Args:
        dataset_id: Dataset ID to validate
        
    Returns:
        Validated dataset ID
        
    Raises:
        ValidationError: If dataset ID is invalid
    """
    return validate_id_format(dataset_id, "Dataset ID")


def validate_application_profile_id(profile_id: Optional[str]) -> str:
    """
    Validate application profile ID.
    
    Args:
        profile_id: Application profile ID to validate
        
    Returns:
        Validated application profile ID
        
    Raises:
        ValidationError: If application profile ID is invalid
    """
    return validate_id_format(profile_id, "Application profile ID")


def validate_test_case_id(test_case_id: Optional[str]) -> str:
    """
    Validate test case ID.
    
    Args:
        test_case_id: Test case ID to validate
        
    Returns:
        Validated test case ID
        
    Raises:
        ValidationError: If test case ID is invalid
    """
    return validate_id_format(test_case_id, "Test case ID")


def validate_evaluation_run_id(run_id: Optional[str]) -> str:
    """
    Validate evaluation run ID.
    
    Args:
        run_id: Evaluation run ID to validate
        
    Returns:
        Validated evaluation run ID
        
    Raises:
        ValidationError: If evaluation run ID is invalid
    """
    return validate_id_format(run_id, "Evaluation run ID")


def validate_string_field(
    value: Optional[str],
    field_name: str,
    min_length: int = 1,
    max_length: Optional[int] = None,
    allow_empty: bool = False,
    pattern: Optional[str] = None
) -> str:
    """
    Validate a string field.
    
    Args:
        value: String value to validate
        field_name: Name of the field for error messages
        min_length: Minimum length (default: 1)
        max_length: Maximum length (optional)
        allow_empty: Whether to allow empty strings (default: False)
        pattern: Regex pattern to match (optional)
        
    Returns:
        Validated and stripped string
        
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if not allow_empty:
            raise ValidationError(f"{field_name} is required")
        return ""
    
    stripped = value.strip()
    
    if not allow_empty and not stripped:
        raise ValidationError(f"{field_name} cannot be empty or whitespace only")
    
    # If empty is allowed and string is empty, skip length checks
    if allow_empty and not stripped:
        return stripped
    
    if len(stripped) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} character(s) long"
        )
    
    if max_length is not None and len(stripped) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} character(s) long"
        )
    
    if pattern is not None and not re.match(pattern, stripped):
        raise ValidationError(f"{field_name} format is invalid")
    
    return stripped


def validate_list_not_empty(
    value: list,
    field_name: str,
    min_items: int = 1
) -> list:
    """
    Validate a list is not empty.
    
    Args:
        value: List to validate
        field_name: Name of the field for error messages
        min_items: Minimum number of items required
        
    Returns:
        Validated list
        
    Raises:
        ValidationError: If list is empty or too small
    """
    if not value:
        raise ValidationError(f"{field_name} cannot be empty")
    
    if len(value) < min_items:
        raise ValidationError(
            f"{field_name} must contain at least {min_items} item(s)"
        )
    
    return value
