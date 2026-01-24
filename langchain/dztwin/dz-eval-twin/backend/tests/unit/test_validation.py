"""Unit tests for validation utilities."""

import pytest

from app.middleware.error_handler import ValidationError
from app.utils.validation import (
    validate_url,
    validate_phone_number,
    validate_id_format,
    validate_customer_id,
    validate_dataset_id,
    validate_application_profile_id,
    validate_test_case_id,
    validate_evaluation_run_id,
    validate_string_field,
    validate_list_not_empty
)


class TestValidateUrl:
    """Tests for URL validation."""
    
    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        url = "http://example.com/api/v1"
        result = validate_url(url)
        assert result == url
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        url = "https://api.example.com/v1/chat"
        result = validate_url(url)
        assert result == url
    
    def test_url_with_port(self):
        """Test URL with port number."""
        url = "https://localhost:8000/api"
        result = validate_url(url)
        assert result == url
    
    def test_url_with_query_params(self):
        """Test URL with query parameters."""
        url = "https://example.com/api?key=value&foo=bar"
        result = validate_url(url)
        assert result == url
    
    def test_url_with_fragment(self):
        """Test URL with fragment."""
        url = "https://example.com/docs#section"
        result = validate_url(url)
        assert result == url
    
    def test_url_strips_whitespace(self):
        """Test URL with leading/trailing whitespace."""
        url = "  https://example.com/api  "
        result = validate_url(url)
        assert result == "https://example.com/api"
    
    def test_empty_url(self):
        """Test empty URL raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("")
        assert "URL is required" in str(exc_info.value)
    
    def test_whitespace_only_url(self):
        """Test whitespace-only URL raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("   ")
        assert "cannot be empty or whitespace only" in str(exc_info.value)
    
    def test_url_without_protocol(self):
        """Test URL without http/https protocol."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("example.com/api")
        assert "must start with http:// or https://" in str(exc_info.value)
    
    def test_url_with_ftp_protocol(self):
        """Test URL with unsupported protocol."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("ftp://example.com/file")
        assert "must start with http:// or https://" in str(exc_info.value)
    
    def test_url_without_domain(self):
        """Test URL without domain."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("https://")
        assert "must have a valid domain" in str(exc_info.value)
    
    def test_url_too_long(self):
        """Test URL exceeding maximum length."""
        long_url = "https://example.com/" + "a" * 2050
        with pytest.raises(ValidationError) as exc_info:
            validate_url(long_url)
        assert "too long" in str(exc_info.value)
    
    def test_custom_field_name(self):
        """Test custom field name in error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("", "Endpoint")
        assert "Endpoint is required" in str(exc_info.value)


class TestValidatePhoneNumber:
    """Tests for phone number validation."""
    
    def test_valid_us_phone(self):
        """Test valid US phone number."""
        phone = "+1-555-0100"
        result = validate_phone_number(phone)
        assert result == phone
    
    def test_valid_international_phone(self):
        """Test valid international phone number."""
        phone = "+44 20 7946 0958"
        result = validate_phone_number(phone)
        assert result == phone
    
    def test_phone_with_parentheses(self):
        """Test phone number with parentheses."""
        phone = "(555) 123-4567"
        result = validate_phone_number(phone)
        assert result == phone
    
    def test_phone_with_dots(self):
        """Test phone number with dots."""
        phone = "555.123.4567"
        result = validate_phone_number(phone)
        assert result == phone
    
    def test_phone_digits_only(self):
        """Test phone number with digits only."""
        phone = "5551234567"
        result = validate_phone_number(phone)
        assert result == phone
    
    def test_phone_strips_whitespace(self):
        """Test phone number with leading/trailing whitespace."""
        phone = "  +1-555-0100  "
        result = validate_phone_number(phone)
        assert result == "+1-555-0100"
    
    def test_none_phone(self):
        """Test None phone number returns None."""
        result = validate_phone_number(None)
        assert result is None
    
    def test_empty_phone(self):
        """Test empty phone number returns None."""
        result = validate_phone_number("")
        assert result is None
    
    def test_whitespace_only_phone(self):
        """Test whitespace-only phone number returns None."""
        result = validate_phone_number("   ")
        assert result is None
    
    def test_phone_without_digits(self):
        """Test phone number without any digits."""
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("abc-def-ghij")
        assert "must contain at least one digit" in str(exc_info.value)
    
    def test_phone_with_invalid_characters(self):
        """Test phone number with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("+1-555-0100#ext123")
        assert "contains invalid characters" in str(exc_info.value)
    
    def test_phone_too_long(self):
        """Test phone number exceeding maximum length."""
        long_phone = "1" * 35
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number(long_phone)
        assert "too long" in str(exc_info.value)
    
    def test_custom_field_name(self):
        """Test custom field name in error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("abc", "Contact phone")
        assert "Contact phone must contain at least one digit" in str(exc_info.value)


class TestValidateIdFormat:
    """Tests for ID format validation."""
    
    def test_valid_id(self):
        """Test valid ID."""
        id_value = "cust_123456"
        result = validate_id_format(id_value)
        assert result == id_value
    
    def test_id_strips_whitespace(self):
        """Test ID with leading/trailing whitespace."""
        id_value = "  cust_123456  "
        result = validate_id_format(id_value)
        assert result == "cust_123456"
    
    def test_empty_id(self):
        """Test empty ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format("")
        assert "ID is required" in str(exc_info.value)
    
    def test_whitespace_only_id(self):
        """Test whitespace-only ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format("   ")
        assert "cannot be empty or whitespace only" in str(exc_info.value)
    
    def test_id_too_long(self):
        """Test ID exceeding maximum length."""
        long_id = "id_" + "a" * 200
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format(long_id)
        assert "too long" in str(exc_info.value)
    
    def test_custom_field_name(self):
        """Test custom field name in error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_id_format("", "Customer ID")
        assert "Customer ID is required" in str(exc_info.value)


class TestSpecificIdValidators:
    """Tests for specific ID validators."""
    
    def test_validate_customer_id(self):
        """Test customer ID validation."""
        result = validate_customer_id("cust_123")
        assert result == "cust_123"
    
    def test_validate_dataset_id(self):
        """Test dataset ID validation."""
        result = validate_dataset_id("dataset_456")
        assert result == "dataset_456"
    
    def test_validate_application_profile_id(self):
        """Test application profile ID validation."""
        result = validate_application_profile_id("app_789")
        assert result == "app_789"
    
    def test_validate_test_case_id(self):
        """Test test case ID validation."""
        result = validate_test_case_id("tc_001")
        assert result == "tc_001"
    
    def test_validate_evaluation_run_id(self):
        """Test evaluation run ID validation."""
        result = validate_evaluation_run_id("run_abc")
        assert result == "run_abc"
    
    def test_invalid_customer_id(self):
        """Test invalid customer ID."""
        with pytest.raises(ValidationError) as exc_info:
            validate_customer_id("")
        assert "Customer ID is required" in str(exc_info.value)


class TestValidateStringField:
    """Tests for string field validation."""
    
    def test_valid_string(self):
        """Test valid string."""
        result = validate_string_field("Test Name", "Name")
        assert result == "Test Name"
    
    def test_string_strips_whitespace(self):
        """Test string with leading/trailing whitespace."""
        result = validate_string_field("  Test Name  ", "Name")
        assert result == "Test Name"
    
    def test_string_min_length(self):
        """Test string minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("", "Name", min_length=1)
        # Empty string triggers the "cannot be empty" check first
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_string_max_length(self):
        """Test string maximum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("a" * 100, "Name", max_length=50)
        assert "must be at most 50 character(s) long" in str(exc_info.value)
    
    def test_string_pattern_match(self):
        """Test string pattern matching."""
        result = validate_string_field("test123", "Username", pattern=r'^[a-z0-9]+$')
        assert result == "test123"
    
    def test_string_pattern_no_match(self):
        """Test string pattern not matching."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field("Test@123", "Username", pattern=r'^[a-z0-9]+$')
        assert "format is invalid" in str(exc_info.value)
    
    def test_string_allow_empty(self):
        """Test string with allow_empty=True."""
        result = validate_string_field("", "Description", allow_empty=True)
        assert result == ""
    
    def test_string_none_not_allowed(self):
        """Test None string when not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_field(None, "Name", allow_empty=False)
        assert "Name is required" in str(exc_info.value)
    
    def test_string_none_allowed(self):
        """Test None string when allowed."""
        result = validate_string_field(None, "Description", allow_empty=True)
        assert result == ""


class TestValidateListNotEmpty:
    """Tests for list validation."""
    
    def test_valid_list(self):
        """Test valid non-empty list."""
        items = ["item1", "item2"]
        result = validate_list_not_empty(items, "Items")
        assert result == items
    
    def test_empty_list(self):
        """Test empty list raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list_not_empty([], "Items")
        assert "Items cannot be empty" in str(exc_info.value)
    
    def test_list_min_items(self):
        """Test list minimum items validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list_not_empty(["item1"], "Items", min_items=2)
        assert "must contain at least 2 item(s)" in str(exc_info.value)
    
    def test_list_meets_min_items(self):
        """Test list meeting minimum items requirement."""
        items = ["item1", "item2", "item3"]
        result = validate_list_not_empty(items, "Items", min_items=2)
        assert result == items


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_url_with_unicode_domain(self):
        """Test URL with unicode characters in domain."""
        url = "https://例え.jp/api"
        result = validate_url(url)
        assert result == url
    
    def test_phone_with_extension(self):
        """Test phone number with extension notation."""
        # Extensions with # are not allowed per our validation
        phone = "+1-555-0100"
        result = validate_phone_number(phone)
        assert result == phone
    
    def test_id_with_special_characters(self):
        """Test ID with underscores and hyphens."""
        id_value = "cust_123-abc_456"
        result = validate_id_format(id_value)
        assert result == id_value
    
    def test_string_with_newlines(self):
        """Test string field with newlines."""
        text = "Line 1\nLine 2\nLine 3"
        result = validate_string_field(text, "Description", max_length=100)
        assert result == text
    
    def test_url_at_max_length(self):
        """Test URL at exactly maximum length."""
        # Create URL that's exactly 2048 characters
        base = "https://example.com/"
        path = "a" * (2048 - len(base))
        url = base + path
        result = validate_url(url)
        assert result == url
        assert len(result) == 2048
    
    def test_phone_at_max_length(self):
        """Test phone number at exactly maximum length."""
        phone = "+" + "1" * 29  # 30 characters total
        result = validate_phone_number(phone)
        assert result == phone
        assert len(result) == 30
    
    def test_id_at_max_length(self):
        """Test ID at exactly maximum length."""
        id_value = "id_" + "a" * 197  # 200 characters total (3 + 197)
        result = validate_id_format(id_value)
        assert result == id_value
        assert len(result) == 200
