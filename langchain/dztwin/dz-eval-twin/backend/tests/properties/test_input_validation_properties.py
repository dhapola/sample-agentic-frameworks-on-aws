"""Property-based tests for input validation rejection.

Feature: gen-ai-eval-platform
Property: Input validation rejects invalid data
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError as PydanticValidationError

from app.models.customer import Customer
from app.models.dataset import Dataset
from app.models.application_profile import ApplicationProfile, ApplicationType
from app.models.test_case import TestCase
from app.models.connection_config import ConnectionConfig
from app.middleware.error_handler import ValidationError
from app.utils.validation import (
    validate_url,
    validate_phone_number,
    validate_id_format,
    validate_string_field,
    validate_list_not_empty
)


# ==================== Hypothesis Strategies ====================

@st.composite
def invalid_name_strategy(draw):
    """Generate invalid names (empty, whitespace-only, too long)."""
    choice = draw(st.integers(min_value=0, max_value=2))
    if choice == 0:
        # Empty string
        return ""
    elif choice == 1:
        # Whitespace only
        return draw(st.text(alphabet=" \t\n\r", min_size=1, max_size=10))
    else:
        # Too long (>200 characters)
        return draw(st.text(min_size=201, max_size=300))


@st.composite
def invalid_email_strategy(draw):
    """Generate invalid email addresses."""
    choice = draw(st.integers(min_value=0, max_value=5))
    if choice == 0:
        # Missing @ symbol
        return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd')
        )))
    elif choice == 1:
        # Multiple @ symbols
        return "user@@example.com"
    elif choice == 2:
        # Missing domain
        return "user@"
    elif choice == 3:
        # Missing local part
        return "@example.com"
    elif choice == 4:
        # Invalid characters
        return "user name@example.com"
    else:
        # Empty string
        return ""


@st.composite
def invalid_phone_strategy(draw):
    """Generate invalid phone numbers."""
    choice = draw(st.integers(min_value=0, max_value=1))
    if choice == 0:
        # No digits
        return draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz-() "))
    else:
        # Too long
        return "1" * 35


@st.composite
def invalid_url_strategy(draw):
    """Generate invalid URLs."""
    choice = draw(st.integers(min_value=0, max_value=3))
    if choice == 0:
        # Empty string
        return ""
    elif choice == 1:
        # Whitespace only
        return "   "
    elif choice == 2:
        # Missing protocol
        return "example.com/api"
    else:
        # Missing domain
        return "https://"


@st.composite
def invalid_id_strategy(draw):
    """Generate invalid IDs."""
    choice = draw(st.integers(min_value=0, max_value=1))
    if choice == 0:
        # Empty string
        return ""
    else:
        # Whitespace only
        return "   "


@st.composite
def invalid_timeout_strategy(draw):
    """Generate invalid timeout values."""
    choice = draw(st.integers(min_value=0, max_value=2))
    if choice == 0:
        # Too small
        return draw(st.integers(max_value=0))
    elif choice == 1:
        # Too large
        return draw(st.integers(min_value=301, max_value=1000))
    else:
        # Negative
        return draw(st.integers(max_value=-1))


@st.composite
def invalid_retries_strategy(draw):
    """Generate invalid retry values."""
    choice = draw(st.integers(min_value=0, max_value=1))
    if choice == 0:
        # Negative
        return draw(st.integers(max_value=-1))
    else:
        # Too large
        return draw(st.integers(min_value=11, max_value=100))


# ==================== Property Tests ====================

@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_name=invalid_name_strategy())
def test_customer_rejects_invalid_name(invalid_name: str):
    """
    Property 21: Input validation rejects invalid data (Customer name).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid customer name (empty, whitespace-only, too long),
    the Customer model should reject the input with a ValidationError.
    """
    # Attempt to create Customer with invalid name
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Customer(
            id="cust_test_123",
            name=invalid_name,
            contact_email="test@example.com"
        )
    
    # Property: Error message should be specific and informative
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "name", "empty", "whitespace", "long", "validation", "string"
    ]), f"Error message should mention the validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_email=invalid_email_strategy())
def test_customer_rejects_invalid_email(invalid_email: str):
    """
    Property 21: Input validation rejects invalid data (Customer email).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid email address, the Customer model should reject
    the input with a ValidationError.
    """
    # Attempt to create Customer with invalid email
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Customer(
            id="cust_test_123",
            name="Test Customer",
            contact_email=invalid_email
        )
    
    # Property: Error message should mention email validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "email", "validation", "invalid", "value"
    ]), f"Error message should mention email validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_phone=st.text(
    min_size=1, 
    max_size=20, 
    alphabet="abcdefghijklmnopqrstuvwxyz-() "
).filter(lambda x: x.strip() != ""))  # Exclude whitespace-only strings
def test_customer_rejects_invalid_phone(invalid_phone: str):
    """
    Property 21: Input validation rejects invalid data (Customer phone).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid phone number (no digits, non-whitespace), the Customer 
    model should reject the input with a ValidationError.
    """
    # Attempt to create Customer with invalid phone
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Customer(
            id="cust_test_123",
            name="Test Customer",
            contact_email="test@example.com",
            contact_phone=invalid_phone
        )
    
    # Property: Error message should mention phone validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "phone", "digit", "character", "validation"
    ]), f"Error message should mention phone validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_name=invalid_name_strategy())
def test_dataset_rejects_invalid_name(invalid_name: str):
    """
    Property 21: Input validation rejects invalid data (Dataset name).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid dataset name, the Dataset model should reject
    the input with a ValidationError.
    """
    # Attempt to create Dataset with invalid name
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Dataset(
            id="dataset_test_123",
            customer_id="cust_123",
            name=invalid_name,
            description="Test description"
        )
    
    # Property: Error message should be specific
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "name", "empty", "whitespace", "long", "validation", "string"
    ]), f"Error message should mention the validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_id=invalid_id_strategy())
def test_dataset_rejects_invalid_customer_id(invalid_id: str):
    """
    Property 21: Input validation rejects invalid data (Dataset customer_id).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid customer ID, the Dataset model should reject
    the input with a ValidationError.
    """
    # Attempt to create Dataset with invalid customer_id
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Dataset(
            id="dataset_test_123",
            customer_id=invalid_id,
            name="Test Dataset",
            description="Test description"
        )
    
    # Property: Error message should mention customer ID
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "customer", "id", "empty", "validation"
    ]), f"Error message should mention customer ID validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(data=st.data())
def test_testcase_rejects_invalid_input(data):
    """
    Property 21: Input validation rejects invalid data (TestCase input).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid test case input (empty, whitespace-only),
    the TestCase model should reject the input with a ValidationError.
    """
    # Generate invalid input (empty or whitespace-only, not too long)
    choice = data.draw(st.integers(min_value=0, max_value=1))
    if choice == 0:
        invalid_input = ""
    else:
        invalid_input = data.draw(st.text(alphabet=" \t\n\r", min_size=1, max_size=10))
    
    # Attempt to create TestCase with invalid input
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        TestCase(
            id="tc_test_001",
            input=invalid_input
        )
    
    # Property: Error message should mention input validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "input", "empty", "whitespace", "validation", "string"
    ]), f"Error message should mention input validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_name=invalid_name_strategy())
def test_application_profile_rejects_invalid_name(invalid_name: str):
    """
    Property 21: Input validation rejects invalid data (ApplicationProfile name).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid profile name, the ApplicationProfile model should
    reject the input with a ValidationError.
    """
    # Attempt to create ApplicationProfile with invalid name
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        ApplicationProfile(
            id="app_test_123",
            customer_id="cust_123",
            name=invalid_name,
            type="chatbot",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com/v1/chat",
                timeout=30,
                retries=3
            )
        )
    
    # Property: Error message should be specific
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "name", "empty", "whitespace", "long", "validation", "string"
    ]), f"Error message should mention the validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_url=invalid_url_strategy())
def test_connection_config_rejects_invalid_endpoint(invalid_url: str):
    """
    Property 21: Input validation rejects invalid data (ConnectionConfig endpoint).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid endpoint URL, the ConnectionConfig model should
    reject the input with a ValidationError.
    """
    # Attempt to create ConnectionConfig with invalid endpoint
    with pytest.raises((PydanticValidationError, ValueError, Exception)) as exc_info:
        ConnectionConfig(
            endpoint=invalid_url,
            timeout=30,
            retries=3
        )
    
    # Property: Error message should mention URL/endpoint validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "url", "endpoint", "invalid", "validation", "scheme", "input"
    ]), f"Error message should mention URL validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_timeout=invalid_timeout_strategy())
def test_connection_config_rejects_invalid_timeout(invalid_timeout: int):
    """
    Property 21: Input validation rejects invalid data (ConnectionConfig timeout).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid timeout value (negative, zero, too large),
    the ConnectionConfig model should reject the input with a ValidationError.
    """
    # Attempt to create ConnectionConfig with invalid timeout
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=invalid_timeout,
            retries=3
        )
    
    # Property: Error message should mention timeout validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "timeout", "greater", "less", "validation", "second"
    ]), f"Error message should mention timeout validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_retries=invalid_retries_strategy())
def test_connection_config_rejects_invalid_retries(invalid_retries: int):
    """
    Property 21: Input validation rejects invalid data (ConnectionConfig retries).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid retries value (negative, too large),
    the ConnectionConfig model should reject the input with a ValidationError.
    """
    # Attempt to create ConnectionConfig with invalid retries
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        ConnectionConfig(
            endpoint="https://api.example.com/v1/chat",
            timeout=30,
            retries=invalid_retries
        )
    
    # Property: Error message should mention retries validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "retries", "retry", "greater", "less", "validation", "negative"
    ]), f"Error message should mention retries validation: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
def test_dataset_rejects_duplicate_test_case_ids(data):
    """
    Property 21: Input validation rejects invalid data (duplicate test case IDs).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any dataset with duplicate test case IDs, the Dataset model
    should reject the input with a ValidationError.
    """
    # Generate a test case ID
    tc_id = data.draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'
    )))
    
    # Create two test cases with the same ID
    test_cases = [
        TestCase(id=tc_id, input="Test input 1"),
        TestCase(id=tc_id, input="Test input 2")
    ]
    
    # Attempt to create Dataset with duplicate test case IDs
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Dataset(
            id="dataset_test_123",
            customer_id="cust_123",
            name="Test Dataset",
            description="Test description",
            test_cases=test_cases
        )
    
    # Property: Error message should mention duplicate IDs
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "unique", "duplicate", "id", "test case"
    ]), f"Error message should mention duplicate test case IDs: {exc_info.value}"


# ==================== Validation Utility Tests ====================

@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_url=invalid_url_strategy())
def test_validate_url_rejects_invalid_urls(invalid_url: str):
    """
    Property 21: Input validation rejects invalid data (validate_url utility).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid URL, the validate_url utility should raise
    ValidationError with a specific message.
    """
    # Attempt to validate invalid URL
    with pytest.raises(ValidationError) as exc_info:
        validate_url(invalid_url)
    
    # Property: Error message should be specific and informative
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "url", "required", "empty", "whitespace", "http", "https", "domain", "long"
    ]), f"Error message should mention URL validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_phone=invalid_phone_strategy())
def test_validate_phone_rejects_invalid_phones(invalid_phone: str):
    """
    Property 21: Input validation rejects invalid data (validate_phone_number utility).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid phone number (no digits, non-whitespace), the 
    validate_phone_number utility should raise ValidationError with a specific message.
    """
    # Filter out whitespace-only strings (they return None, not error)
    if invalid_phone.strip() == "":
        return
    
    # Attempt to validate invalid phone number
    with pytest.raises(ValidationError) as exc_info:
        validate_phone_number(invalid_phone)
    
    # Property: Error message should be specific
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "phone", "digit", "character", "long"
    ]), f"Error message should mention phone validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(invalid_id=invalid_id_strategy())
def test_validate_id_rejects_invalid_ids(invalid_id: str):
    """
    Property 21: Input validation rejects invalid data (validate_id_format utility).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid ID, the validate_id_format utility should raise
    ValidationError with a specific message.
    """
    # Attempt to validate invalid ID
    with pytest.raises(ValidationError) as exc_info:
        validate_id_format(invalid_id)
    
    # Property: Error message should be specific
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "id", "required", "empty", "whitespace", "long"
    ]), f"Error message should mention ID validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=15, deadline=None)
@given(
    invalid_value=st.one_of(
        st.just(""),
        st.text(alphabet=" \t\n", min_size=1, max_size=10),
        st.text(min_size=201, max_size=300)
    )
)
def test_validate_string_field_rejects_invalid_strings(invalid_value: str):
    """
    Property 21: Input validation rejects invalid data (validate_string_field utility).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid string (empty, whitespace-only, too long),
    the validate_string_field utility should raise ValidationError.
    """
    # Attempt to validate invalid string with max_length=200
    with pytest.raises(ValidationError) as exc_info:
        validate_string_field(invalid_value, "TestField", min_length=1, max_length=200)
    
    # Property: Error message should be specific
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "testfield", "required", "empty", "whitespace", "long", "character"
    ]), f"Error message should mention string validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
def test_validate_list_rejects_empty_list():
    """
    Property 21: Input validation rejects invalid data (validate_list_not_empty utility).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any empty list, the validate_list_not_empty utility should
    raise ValidationError with a specific message.
    """
    # Attempt to validate empty list
    with pytest.raises(ValidationError) as exc_info:
        validate_list_not_empty([], "TestList")
    
    # Property: Error message should mention empty list
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "testlist", "empty", "cannot"
    ]), f"Error message should mention empty list: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(min_items=st.integers(min_value=2, max_value=5))
def test_validate_list_rejects_insufficient_items(min_items: int):
    """
    Property 21: Input validation rejects invalid data (list min_items).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any list with fewer items than required, the validate_list_not_empty
    utility should raise ValidationError with a specific message.
    """
    # Create list with one fewer item than required
    items = ["item"] * (min_items - 1)
    
    # Attempt to validate list with insufficient items
    with pytest.raises(ValidationError) as exc_info:
        validate_list_not_empty(items, "TestList", min_items=min_items)
    
    # Property: Error message should mention minimum items requirement
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "testlist", "contain", "least", "item"
    ]), f"Error message should mention minimum items: {exc_info.value}"
    assert str(min_items) in str(exc_info.value), \
        f"Error message should mention required count {min_items}: {exc_info.value}"


# ==================== Combined Validation Tests ====================

@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
def test_multiple_validation_errors_in_customer(data):
    """
    Property 21: Input validation rejects invalid data (multiple errors).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any entity with multiple invalid fields, validation should
    fail and report at least one of the validation errors.
    """
    # Generate multiple invalid fields
    invalid_name = data.draw(invalid_name_strategy())
    invalid_email = data.draw(invalid_email_strategy())
    
    # Attempt to create Customer with multiple invalid fields
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        Customer(
            id="cust_test_123",
            name=invalid_name,
            contact_email=invalid_email
        )
    
    # Property: At least one validation error should be reported
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "name", "email", "validation", "invalid", "empty"
    ]), f"Error message should mention at least one validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(data=st.data())
def test_multiple_validation_errors_in_connection_config(data):
    """
    Property 21: Input validation rejects invalid data (multiple config errors).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any ConnectionConfig with multiple invalid fields, validation
    should fail and report at least one of the validation errors.
    """
    # Generate multiple invalid fields
    invalid_url = data.draw(invalid_url_strategy())
    invalid_timeout = data.draw(invalid_timeout_strategy())
    
    # Attempt to create ConnectionConfig with multiple invalid fields
    with pytest.raises((PydanticValidationError, ValueError, Exception)) as exc_info:
        ConnectionConfig(
            endpoint=invalid_url,
            timeout=invalid_timeout,
            retries=3
        )
    
    # Property: At least one validation error should be reported
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "url", "endpoint", "timeout", "validation", "invalid", "greater", "less"
    ]), f"Error message should mention at least one validation issue: {exc_info.value}"


@pytest.mark.timeout(60)
@settings(max_examples=10, deadline=None)
@given(
    invalid_type=st.text(min_size=1, max_size=20).filter(
        lambda x: x not in ["chatbot", "rag", "agent", "workflow", "custom"]
    )
)
def test_application_profile_rejects_invalid_type(invalid_type: str):
    """
    Property 21: Input validation rejects invalid data (ApplicationProfile type).
    
    **Validates: Requirements 7.4, 7.5**
    
    For any invalid application type (not in allowed list),
    the ApplicationProfile model should reject the input with a ValidationError.
    """
    # Attempt to create ApplicationProfile with invalid type
    with pytest.raises((PydanticValidationError, ValueError)) as exc_info:
        ApplicationProfile(
            id="app_test_123",
            customer_id="cust_123",
            name="Test Profile",
            type=invalid_type,
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com/v1/chat",
                timeout=30,
                retries=3
            )
        )
    
    # Property: Error message should mention type validation
    error_str = str(exc_info.value).lower()
    assert any(keyword in error_str for keyword in [
        "type", "input", "literal", "validation"
    ]), f"Error message should mention type validation: {exc_info.value}"
