"""Unit tests for ApplicationProfileService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.application_profile_service import ApplicationProfileService
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.customer import Customer


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return MagicMock()


@pytest.fixture
def profile_service(mock_repository):
    """Create an ApplicationProfileService with mock repository."""
    return ApplicationProfileService(mock_repository)


@pytest.fixture
def sample_customer():
    """Create a sample customer."""
    return Customer(
        id="cust_123",
        name="Test Customer",
        contact_email="test@example.com",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_profile():
    """Create a sample application profile."""
    return ApplicationProfile(
        id="app_123",
        customer_id="cust_123",
        name="Test Profile",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# ==================== Create Profile Tests ====================

@pytest.mark.asyncio
async def test_create_profile_success(profile_service, mock_repository, sample_customer, sample_profile):
    """Test successful profile creation."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    mock_repository.create_application_profile = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Test Profile",
        app_type="chatbot",
        endpoint="https://api.example.com"
    )
    
    assert result.name == "Test Profile"
    assert result.type == "chatbot"
    assert result.customer_id == "cust_123"
    mock_repository.create_application_profile.assert_called_once()


@pytest.mark.asyncio
async def test_create_profile_empty_customer_id(profile_service):
    """Test creating profile with empty customer ID fails."""
    with pytest.raises(ValueError, match="Customer ID is required"):
        await profile_service.create_application_profile(
            customer_id="",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com"
        )


@pytest.mark.asyncio
async def test_create_profile_empty_name(profile_service, mock_repository, sample_customer):
    """Test creating profile with empty name fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Profile name is required"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="",
            app_type="chatbot",
            endpoint="https://api.example.com"
        )


@pytest.mark.asyncio
async def test_create_profile_empty_app_type(profile_service, mock_repository, sample_customer):
    """Test creating profile with empty app type fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Application type is required"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="",
            endpoint="https://api.example.com"
        )


@pytest.mark.asyncio
async def test_create_profile_invalid_app_type(profile_service, mock_repository, sample_customer):
    """Test creating profile with invalid app type fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Invalid application type"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="invalid_type",
            endpoint="https://api.example.com"
        )


@pytest.mark.asyncio
async def test_create_profile_valid_app_types(profile_service, mock_repository, sample_customer, sample_profile):
    """Test creating profile with all valid app types."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    mock_repository.create_application_profile = AsyncMock(return_value=sample_profile)
    
    valid_types = ["chatbot", "rag", "agent", "workflow", "custom"]
    
    for app_type in valid_types:
        result = await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type=app_type,
            endpoint="https://api.example.com"
        )
        assert result is not None


@pytest.mark.asyncio
async def test_create_profile_empty_endpoint(profile_service, mock_repository, sample_customer):
    """Test creating profile with empty endpoint fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Endpoint is required"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint=""
        )


@pytest.mark.asyncio
async def test_create_profile_invalid_endpoint_no_protocol(profile_service, mock_repository, sample_customer):
    """Test creating profile with endpoint missing protocol fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Endpoint must be a valid HTTP or HTTPS URL"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint="api.example.com"
        )


@pytest.mark.asyncio
async def test_create_profile_invalid_timeout_too_low(profile_service, mock_repository, sample_customer):
    """Test creating profile with timeout too low fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Timeout must be between 1 and 300 seconds"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com",
            timeout=0
        )


@pytest.mark.asyncio
async def test_create_profile_invalid_timeout_too_high(profile_service, mock_repository, sample_customer):
    """Test creating profile with timeout too high fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Timeout must be between 1 and 300 seconds"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com",
            timeout=301
        )


@pytest.mark.asyncio
async def test_create_profile_invalid_retries_negative(profile_service, mock_repository, sample_customer):
    """Test creating profile with negative retries fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Retries must be between 0 and 10"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com",
            retries=-1
        )


@pytest.mark.asyncio
async def test_create_profile_invalid_retries_too_high(profile_service, mock_repository, sample_customer):
    """Test creating profile with retries too high fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    with pytest.raises(ValueError, match="Retries must be between 0 and 10"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com",
            retries=11
        )


@pytest.mark.asyncio
async def test_create_profile_customer_not_found(profile_service, mock_repository):
    """Test creating profile for non-existent customer fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="Customer with ID cust_123 not found"):
        await profile_service.create_application_profile(
            customer_id="cust_123",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com"
        )


@pytest.mark.asyncio
async def test_create_profile_with_authentication(profile_service, mock_repository, sample_customer, sample_profile):
    """Test creating profile with authentication."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    sample_profile.connection_config.authentication = {"type": "bearer", "token": "secret"}
    mock_repository.create_application_profile = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Test Profile",
        app_type="chatbot",
        endpoint="https://api.example.com",
        authentication={"type": "bearer", "token": "secret"}
    )
    
    assert result.connection_config.authentication is not None


@pytest.mark.asyncio
async def test_create_profile_with_custom_headers(profile_service, mock_repository, sample_customer, sample_profile):
    """Test creating profile with custom headers."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    sample_profile.connection_config.custom_headers = {"X-Custom": "value"}
    mock_repository.create_application_profile = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Test Profile",
        app_type="chatbot",
        endpoint="https://api.example.com",
        custom_headers={"X-Custom": "value"}
    )
    
    assert result.connection_config.custom_headers is not None


# ==================== Get Profile Tests ====================

@pytest.mark.asyncio
async def test_get_profile_success(profile_service, mock_repository, sample_profile):
    """Test successful profile retrieval."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.get_application_profile("app_123")
    
    assert result is not None
    assert result.id == "app_123"
    mock_repository.get_application_profile_by_id.assert_called_once_with("app_123")


@pytest.mark.asyncio
async def test_get_profile_not_found(profile_service, mock_repository):
    """Test getting non-existent profile returns None."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=None)
    
    result = await profile_service.get_application_profile("nonexistent")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_profile_empty_id(profile_service):
    """Test getting profile with empty ID fails."""
    with pytest.raises(ValueError, match="Profile ID is required"):
        await profile_service.get_application_profile("")


# ==================== Get Profiles by Customer Tests ====================

@pytest.mark.asyncio
async def test_get_profiles_by_customer_success(profile_service, mock_repository):
    """Test getting profiles by customer."""
    profiles = [
        ApplicationProfile(
            id="app_1",
            customer_id="cust_123",
            name="Profile 1",
            type="chatbot",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ApplicationProfile(
            id="app_2",
            customer_id="cust_123",
            name="Profile 2",
            type="rag",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    mock_repository.get_application_profiles = AsyncMock(return_value=profiles)
    
    result = await profile_service.get_profiles_by_customer("cust_123")
    
    assert len(result) == 2
    assert all(p.customer_id == "cust_123" for p in result)


@pytest.mark.asyncio
async def test_get_profiles_by_customer_empty(profile_service, mock_repository):
    """Test getting profiles by customer when none exist."""
    mock_repository.get_application_profiles = AsyncMock(return_value=[])
    
    result = await profile_service.get_profiles_by_customer("cust_123")
    
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_profiles_by_customer_empty_id(profile_service):
    """Test getting profiles with empty customer ID fails."""
    with pytest.raises(ValueError, match="Customer ID is required"):
        await profile_service.get_profiles_by_customer("")


# ==================== Get All Profiles Tests ====================

@pytest.mark.asyncio
async def test_get_all_profiles_success(profile_service, mock_repository):
    """Test getting all profiles."""
    profiles = [
        ApplicationProfile(
            id="app_1",
            customer_id="cust_123",
            name="Profile 1",
            type="chatbot",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    mock_repository.get_application_profiles = AsyncMock(return_value=profiles)
    
    result = await profile_service.get_all_profiles()
    
    assert len(result) == 1


# ==================== Update Profile Tests ====================

@pytest.mark.asyncio
async def test_update_profile_name(profile_service, mock_repository, sample_profile):
    """Test updating profile name."""
    sample_profile.name = "Updated Profile"
    mock_repository.update_application_profile = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.update_application_profile(
        profile_id="app_123",
        name="Updated Profile"
    )
    
    assert result.name == "Updated Profile"


@pytest.mark.asyncio
async def test_update_profile_endpoint(profile_service, mock_repository, sample_profile):
    """Test updating profile endpoint."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    sample_profile.connection_config.endpoint = "https://new-api.example.com"
    mock_repository.update_application_profile = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.update_application_profile(
        profile_id="app_123",
        endpoint="https://new-api.example.com"
    )
    
    # HttpUrl may or may not add trailing slash, just check it starts with the URL
    assert str(result.connection_config.endpoint).startswith("https://new-api.example.com")


@pytest.mark.asyncio
async def test_update_profile_empty_name(profile_service):
    """Test updating profile with empty name fails."""
    with pytest.raises(ValueError, match="Profile name cannot be empty"):
        await profile_service.update_application_profile(
            profile_id="app_123",
            name=""
        )


@pytest.mark.asyncio
async def test_update_profile_invalid_endpoint(profile_service, mock_repository, sample_profile):
    """Test updating profile with invalid endpoint fails."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    with pytest.raises(ValueError, match="Endpoint must be a valid HTTP or HTTPS URL"):
        await profile_service.update_application_profile(
            profile_id="app_123",
            endpoint="invalid-url"
        )


@pytest.mark.asyncio
async def test_update_profile_no_updates(profile_service):
    """Test updating profile with no updates fails."""
    with pytest.raises(ValueError, match="No updates provided"):
        await profile_service.update_application_profile(profile_id="app_123")


@pytest.mark.asyncio
async def test_update_profile_empty_id(profile_service):
    """Test updating profile with empty ID fails."""
    with pytest.raises(ValueError, match="Profile ID is required"):
        await profile_service.update_application_profile(
            profile_id="",
            name="Updated"
        )


# ==================== Delete Profile Tests ====================

@pytest.mark.asyncio
async def test_delete_profile_success(profile_service, mock_repository):
    """Test successful profile deletion."""
    mock_repository.delete_application_profile = AsyncMock()
    
    await profile_service.delete_application_profile("app_123")
    
    mock_repository.delete_application_profile.assert_called_once_with("app_123")


@pytest.mark.asyncio
async def test_delete_profile_empty_id(profile_service):
    """Test deleting profile with empty ID fails."""
    with pytest.raises(ValueError, match="Profile ID is required"):
        await profile_service.delete_application_profile("")


# ==================== Validate Profile Tests ====================

@pytest.mark.asyncio
async def test_validate_profile_exists_true(profile_service, mock_repository, sample_profile):
    """Test validating existing profile returns True."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.validate_profile_exists("app_123")
    
    assert result is True


@pytest.mark.asyncio
async def test_validate_profile_exists_false(profile_service, mock_repository):
    """Test validating non-existent profile returns False."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=None)
    
    result = await profile_service.validate_profile_exists("nonexistent")
    
    assert result is False


@pytest.mark.asyncio
async def test_validate_profile_belongs_to_customer_true(profile_service, mock_repository, sample_profile):
    """Test validating profile belongs to customer returns True."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.validate_profile_belongs_to_customer("app_123", "cust_123")
    
    assert result is True


@pytest.mark.asyncio
async def test_validate_profile_belongs_to_customer_false(profile_service, mock_repository, sample_profile):
    """Test validating profile belongs to wrong customer returns False."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.validate_profile_belongs_to_customer("app_123", "wrong_customer")
    
    assert result is False


@pytest.mark.asyncio
async def test_validate_profile_belongs_to_customer_profile_not_found(profile_service, mock_repository):
    """Test validating non-existent profile returns False."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=None)
    
    result = await profile_service.validate_profile_belongs_to_customer("nonexistent", "cust_123")
    
    assert result is False
