"""Unit tests for input validation across all API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.middleware.error_handler import ValidationError, UnauthorizedError
from app.utils.validation import (
    validate_id_format,
    validate_customer_id,
    validate_dataset_id,
    validate_application_profile_id,
    validate_test_case_id,
    validate_evaluation_run_id,
    validate_string_field,
    validate_list_not_empty
)


class TestIDValidation:
    """Test ID validation functions."""
    
    def test_validate_id_format_valid(self):
        """Test validation of valid ID."""
        result = validate_id_format("test_123", "Test ID")
        assert result == "test_123"
    
    def test_validate_id_format_with_whitespace(self):
        """Test validation strips whitespace."""
        result = validate_id_format("  test_123  ", "Test ID")
        assert result == "test_123"
    
    def test_validate_id_format_empty(self):
        """Test validation rejects empty ID."""
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format("", "Test ID")
        assert "Test ID is required" in str(exc_info.value.message)
    
    def test_validate_id_format_whitespace_only(self):
        """Test validation rejects whitespace-only ID."""
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format("   ", "Test ID")
        assert "cannot be empty or whitespace only" in str(exc_info.value.message)
    
    def test_validate_id_format_too_long(self):
        """Test validation rejects ID that's too long."""
        long_id = "x" * 201
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format(long_id, "Test ID")
        assert "too long" in str(exc_info.value.message)
    
    def test_validate_customer_id(self):
        """Test customer ID validation."""
        result = validate_customer_id("cust_123")
        assert result == "cust_123"
    
    def test_validate_customer_id_invalid(self):
        """Test customer ID validation rejects empty."""
        with pytest.raises(ValidationError) as exc_info:
            validate_customer_id("")
        assert "Customer ID is required" in str(exc_info.value.message)
    
    def test_validate_dataset_id(self):
        """Test dataset ID validation."""
        result = validate_dataset_id("ds_123")
        assert result == "ds_123"
    
    def test_validate_application_profile_id(self):
        """Test application profile ID validation."""
        result = validate_application_profile_id("prof_123")
        assert result == "prof_123"
    
    def test_validate_test_case_id(self):
        """Test test case ID validation."""
        result = validate_test_case_id("tc_123")
        assert result == "tc_123"
    
    def test_validate_evaluation_run_id(self):
        """Test evaluation run ID validation."""
        result = validate_evaluation_run_id("run_123")
        assert result == "run_123"


class TestStringFieldValidation:
    """Test string field validation."""
    
    def test_validate_string_field_valid(self):
        """Test validation of valid string."""
        result = validate_string_field("test value", "Test Field")
        assert result == "test value"
    
    def test_validate_string_field_strips_whitespace(self):
        """Test validation strips whitespace."""
        result = validate_string_field("  test value  ", "Test Field")
        assert result == "test value"
    
    def test_validate_string_field_required_missing(self):
        """Test validation rejects missing required field."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field(None, "Test Field")
        assert "Test Field is required" in str(exc_info.value.message)
    
    def test_validate_string_field_empty_not_allowed(self):
        """Test validation rejects empty string when not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("", "Test Field", allow_empty=False)
        assert "cannot be empty or whitespace only" in str(exc_info.value.message)
    
    def test_validate_string_field_empty_allowed(self):
        """Test validation allows empty string when configured."""
        result = validate_string_field("", "Test Field", allow_empty=True)
        assert result == ""
    
    def test_validate_string_field_min_length(self):
        """Test validation enforces minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("ab", "Test Field", min_length=3)
        assert "at least 3 character(s) long" in str(exc_info.value.message)
    
    def test_validate_string_field_max_length(self):
        """Test validation enforces maximum length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("abcdef", "Test Field", max_length=5)
        assert "at most 5 character(s) long" in str(exc_info.value.message)
    
    def test_validate_string_field_pattern_match(self):
        """Test validation enforces pattern matching."""
        result = validate_string_field("test123", "Test Field", pattern=r"^[a-z0-9]+$")
        assert result == "test123"
    
    def test_validate_string_field_pattern_no_match(self):
        """Test validation rejects pattern mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("test@123", "Test Field", pattern=r"^[a-z0-9]+$")
        assert "format is invalid" in str(exc_info.value.message)


class TestListValidation:
    """Test list validation."""
    
    def test_validate_list_not_empty_valid(self):
        """Test validation of non-empty list."""
        result = validate_list_not_empty([1, 2, 3], "Test List")
        assert result == [1, 2, 3]
    
    def test_validate_list_not_empty_empty(self):
        """Test validation rejects empty list."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list_not_empty([], "Test List")
        assert "Test List cannot be empty" in str(exc_info.value.message)
    
    def test_validate_list_not_empty_min_items(self):
        """Test validation enforces minimum items."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list_not_empty([1], "Test List", min_items=2)
        assert "at least 2 item(s)" in str(exc_info.value.message)
    
    def test_validate_list_not_empty_meets_min_items(self):
        """Test validation passes when minimum items met."""
        result = validate_list_not_empty([1, 2], "Test List", min_items=2)
        assert result == [1, 2]


class TestAPIEndpointValidation:
    """Test validation in API endpoints."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request with customer context."""
        request = MagicMock()
        request.state.customer_id = "cust_test123"
        return request
    
    @pytest.fixture
    def mock_request_no_customer(self):
        """Create mock request without customer context."""
        request = MagicMock()
        request.state.customer_id = None
        return request
    
    def test_customer_context_required(self, mock_request_no_customer):
        """Test that endpoints require customer context."""
        from app.api.datasets import get_customer_id
        
        with pytest.raises(UnauthorizedError) as exc_info:
            get_customer_id(mock_request_no_customer)
        assert "Customer context required" in str(exc_info.value.message)
    
    def test_customer_context_provided(self, mock_request):
        """Test that customer context is extracted correctly."""
        from app.api.datasets import get_customer_id
        
        customer_id = get_customer_id(mock_request)
        assert customer_id == "cust_test123"


class TestPydanticModelValidation:
    """Test Pydantic model validation in request models."""
    
    def test_create_dataset_request_valid(self):
        """Test valid dataset creation request."""
        from app.api.datasets import CreateDatasetRequest
        
        request = CreateDatasetRequest(
            name="Test Dataset",
            description="Test description"
        )
        assert request.name == "Test Dataset"
        assert request.description == "Test description"
    
    def test_create_dataset_request_name_too_short(self):
        """Test dataset creation request rejects empty name."""
        from app.api.datasets import CreateDatasetRequest
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            CreateDatasetRequest(
                name="",
                description="Test description"
            )
    
    def test_create_dataset_request_name_too_long(self):
        """Test dataset creation request rejects name that's too long."""
        from app.api.datasets import CreateDatasetRequest
        from pydantic import ValidationError as PydanticValidationError
        
        long_name = "x" * 201
        with pytest.raises(PydanticValidationError):
            CreateDatasetRequest(
                name=long_name,
                description="Test description"
            )
    
    def test_create_test_case_request_valid(self):
        """Test valid test case creation request."""
        from app.api.datasets import CreateTestCaseRequest
        
        request = CreateTestCaseRequest(
            input="What is 2+2?",
            expected_output="4"
        )
        assert request.input == "What is 2+2?"
        assert request.expected_output == "4"
    
    def test_create_test_case_request_input_required(self):
        """Test test case creation request requires input."""
        from app.api.datasets import CreateTestCaseRequest
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            CreateTestCaseRequest(
                input="",
                expected_output="4"
            )
    
    def test_create_customer_request_valid(self):
        """Test valid customer creation request."""
        from app.api.customers import CreateCustomerRequest
        
        request = CreateCustomerRequest(
            name="Test Customer",
            contact_email="test@example.com"
        )
        assert request.name == "Test Customer"
        assert request.contact_email == "test@example.com"
    
    def test_create_customer_request_invalid_email(self):
        """Test customer creation request rejects invalid email."""
        from app.api.customers import CreateCustomerRequest
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            CreateCustomerRequest(
                name="Test Customer",
                contact_email="invalid-email"
            )
    
    def test_create_application_profile_request_valid(self):
        """Test valid application profile creation request."""
        from app.api.application_profiles import CreateApplicationProfileRequest
        
        request = CreateApplicationProfileRequest(
            name="Test Profile",
            type="chatbot",
            endpoint="https://api.example.com/chat"
        )
        assert request.name == "Test Profile"
        assert request.type == "chatbot"
        assert request.endpoint == "https://api.example.com/chat"
    
    def test_create_application_profile_request_invalid_type(self):
        """Test application profile creation request rejects invalid type."""
        from app.api.application_profiles import CreateApplicationProfileRequest
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            CreateApplicationProfileRequest(
                name="Test Profile",
                type="invalid_type",
                endpoint="https://api.example.com/chat"
            )
    
    def test_create_application_profile_request_timeout_validation(self):
        """Test application profile creation request validates timeout range."""
        from app.api.application_profiles import CreateApplicationProfileRequest
        from pydantic import ValidationError as PydanticValidationError
        
        # Timeout too low
        with pytest.raises(PydanticValidationError):
            CreateApplicationProfileRequest(
                name="Test Profile",
                type="chatbot",
                endpoint="https://api.example.com/chat",
                timeout=0
            )
        
        # Timeout too high
        with pytest.raises(PydanticValidationError):
            CreateApplicationProfileRequest(
                name="Test Profile",
                type="chatbot",
                endpoint="https://api.example.com/chat",
                timeout=301
            )
    
    def test_start_evaluation_request_valid(self):
        """Test valid evaluation start request."""
        from app.api.evaluations import StartEvaluationRequest
        
        request = StartEvaluationRequest(
            dataset_id="ds_123",
            application_profile_id="prof_123"
        )
        assert request.dataset_id == "ds_123"
        assert request.application_profile_id == "prof_123"
    
    def test_compare_runs_request_valid(self):
        """Test valid compare runs request."""
        from app.api.evaluations import CompareRunsRequest
        
        request = CompareRunsRequest(
            run_ids=["run_1", "run_2", "run_3"]
        )
        assert len(request.run_ids) == 3
    
    def test_compare_runs_request_min_items(self):
        """Test compare runs request requires at least 2 runs."""
        from app.api.evaluations import CompareRunsRequest
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            CompareRunsRequest(
                run_ids=["run_1"]
            )


class TestUpdateRequestValidation:
    """Test validation for update requests."""
    
    def test_update_dataset_request_at_least_one_field(self):
        """Test update dataset request allows partial updates."""
        from app.api.datasets import UpdateDatasetRequest
        
        # Valid: only name
        request = UpdateDatasetRequest(name="New Name")
        assert request.name == "New Name"
        assert request.description is None
        
        # Valid: only description
        request = UpdateDatasetRequest(description="New Description")
        assert request.name is None
        assert request.description == "New Description"
        
        # Valid: both fields
        request = UpdateDatasetRequest(name="New Name", description="New Description")
        assert request.name == "New Name"
        assert request.description == "New Description"
    
    def test_update_customer_request_at_least_one_field(self):
        """Test update customer request allows partial updates."""
        from app.api.customers import UpdateCustomerRequest
        
        # Valid: only name
        request = UpdateCustomerRequest(name="New Name")
        assert request.name == "New Name"
        
        # Valid: only email
        request = UpdateCustomerRequest(contact_email="new@example.com")
        assert request.contact_email == "new@example.com"
    
    def test_update_application_profile_request_at_least_one_field(self):
        """Test update application profile request allows partial updates."""
        from app.api.application_profiles import UpdateApplicationProfileRequest
        
        # Valid: only name
        request = UpdateApplicationProfileRequest(name="New Name")
        assert request.name == "New Name"
        
        # Valid: only timeout
        request = UpdateApplicationProfileRequest(timeout=60)
        assert request.timeout == 60


class TestTenantIsolationValidation:
    """Test tenant isolation validation."""
    
    def test_customer_id_required_for_datasets(self):
        """Test that customer_id is required for dataset operations."""
        from app.api.datasets import get_customer_id
        
        mock_request = MagicMock()
        mock_request.state.customer_id = None
        
        with pytest.raises(UnauthorizedError) as exc_info:
            get_customer_id(mock_request)
        assert "Customer context required" in str(exc_info.value.message)
        assert "X-Customer-ID header" in str(exc_info.value.message)
    
    def test_customer_id_required_for_evaluations(self):
        """Test that customer_id is required for evaluation operations."""
        from app.api.evaluations import get_customer_id
        
        mock_request = MagicMock()
        mock_request.state.customer_id = None
        
        with pytest.raises(UnauthorizedError) as exc_info:
            get_customer_id(mock_request)
        assert "Customer context required" in str(exc_info.value.message)
