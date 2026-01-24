"""Unit tests for customer-profile relationships.

Tests the relationship between customers and application profiles,
ensuring proper linkage and tenant isolation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.customer_service import CustomerService
from app.services.application_profile_service import ApplicationProfileService
from app.models.customer import Customer
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return MagicMock()


@pytest.fixture
def customer_service(mock_repository):
    """Create a CustomerService with mock repository."""
    return CustomerService(mock_repository)


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
def another_customer():
    """Create another sample customer."""
    return Customer(
        id="cust_456",
        name="Another Customer",
        contact_email="another@example.com",
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


# ==================== Customer-Profile Relationship Tests ====================

@pytest.mark.asyncio
async def test_profile_linked_to_correct_customer(profile_service, mock_repository, sample_customer, sample_profile):
    """Test that a profile is correctly linked to its customer."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    mock_repository.create_application_profile = AsyncMock(return_value=sample_profile)
    
    result = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Test Profile",
        app_type="chatbot",
        endpoint="https://api.example.com"
    )
    
    assert result.customer_id == "cust_123"
    assert result.customer_id == sample_customer.id


@pytest.mark.asyncio
async def test_multiple_profiles_for_same_customer(profile_service, mock_repository, sample_customer):
    """Test that multiple profiles can be created for the same customer."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    # Create first profile
    profile1 = ApplicationProfile(
        id="app_1",
        customer_id="cust_123",
        name="Profile 1",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api1.example.com",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_repository.create_application_profile = AsyncMock(return_value=profile1)
    
    result1 = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Profile 1",
        app_type="chatbot",
        endpoint="https://api1.example.com"
    )
    
    # Create second profile
    profile2 = ApplicationProfile(
        id="app_2",
        customer_id="cust_123",
        name="Profile 2",
        type="rag",
        connection_config=ConnectionConfig(
            endpoint="https://api2.example.com",
            timeout=30,
            retries=3
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_repository.create_application_profile = AsyncMock(return_value=profile2)
    
    result2 = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Profile 2",
        app_type="rag",
        endpoint="https://api2.example.com"
    )
    
    # Both profiles should belong to the same customer
    assert result1.customer_id == "cust_123"
    assert result2.customer_id == "cust_123"
    assert result1.id != result2.id


@pytest.mark.asyncio
async def test_profiles_isolated_by_customer(profile_service, mock_repository):
    """Test that profiles are properly isolated by customer."""
    # Customer 1's profiles
    customer1_profiles = [
        ApplicationProfile(
            id="app_1",
            customer_id="cust_123",
            name="Customer 1 Profile",
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
    
    # Customer 2's profiles
    customer2_profiles = [
        ApplicationProfile(
            id="app_2",
            customer_id="cust_456",
            name="Customer 2 Profile",
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
    
    # Mock repository to return different profiles for different customers
    async def mock_get_profiles(customer_id=None):
        if customer_id == "cust_123":
            return customer1_profiles
        elif customer_id == "cust_456":
            return customer2_profiles
        return []
    
    mock_repository.get_application_profiles = mock_get_profiles
    
    # Get profiles for customer 1
    result1 = await profile_service.get_profiles_by_customer("cust_123")
    assert len(result1) == 1
    assert all(p.customer_id == "cust_123" for p in result1)
    
    # Get profiles for customer 2
    result2 = await profile_service.get_profiles_by_customer("cust_456")
    assert len(result2) == 1
    assert all(p.customer_id == "cust_456" for p in result2)
    
    # Verify no cross-contamination
    assert result1[0].id != result2[0].id
    assert result1[0].customer_id != result2[0].customer_id


@pytest.mark.asyncio
async def test_profile_belongs_to_customer_validation(profile_service, mock_repository, sample_profile):
    """Test validation that a profile belongs to a specific customer."""
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    # Profile belongs to cust_123
    assert await profile_service.validate_profile_belongs_to_customer("app_123", "cust_123") is True
    
    # Profile does not belong to cust_456
    assert await profile_service.validate_profile_belongs_to_customer("app_123", "cust_456") is False


@pytest.mark.asyncio
async def test_cannot_create_profile_for_nonexistent_customer(profile_service, mock_repository):
    """Test that creating a profile for a non-existent customer fails."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="Customer with ID nonexistent not found"):
        await profile_service.create_application_profile(
            customer_id="nonexistent",
            name="Test Profile",
            app_type="chatbot",
            endpoint="https://api.example.com"
        )


@pytest.mark.asyncio
async def test_customer_with_no_profiles(profile_service, mock_repository):
    """Test getting profiles for a customer with no profiles."""
    mock_repository.get_application_profiles = AsyncMock(return_value=[])
    
    result = await profile_service.get_profiles_by_customer("cust_123")
    
    assert len(result) == 0
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_different_application_types_for_same_customer(profile_service, mock_repository, sample_customer):
    """Test that a customer can have profiles of different application types."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    app_types = ["chatbot", "rag", "agent", "workflow", "custom"]
    
    for i, app_type in enumerate(app_types):
        profile = ApplicationProfile(
            id=f"app_{i}",
            customer_id="cust_123",
            name=f"{app_type.capitalize()} Profile",
            type=app_type,
            connection_config=ConnectionConfig(
                endpoint=f"https://api{i}.example.com",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_repository.create_application_profile = AsyncMock(return_value=profile)
        
        result = await profile_service.create_application_profile(
            customer_id="cust_123",
            name=f"{app_type.capitalize()} Profile",
            app_type=app_type,
            endpoint=f"https://api{i}.example.com"
        )
        
        assert result.customer_id == "cust_123"
        assert result.type == app_type


@pytest.mark.asyncio
async def test_profile_retains_customer_id_after_update(profile_service, mock_repository, sample_profile):
    """Test that updating a profile does not change its customer_id."""
    # Original profile
    mock_repository.get_application_profile_by_id = AsyncMock(return_value=sample_profile)
    
    # Updated profile (customer_id should remain the same)
    updated_profile = ApplicationProfile(
        id="app_123",
        customer_id="cust_123",  # Should not change
        name="Updated Profile Name",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com",
            timeout=30,
            retries=3
        ),
        created_at=sample_profile.created_at,
        updated_at=datetime.utcnow()
    )
    mock_repository.update_application_profile = AsyncMock(return_value=updated_profile)
    
    result = await profile_service.update_application_profile(
        profile_id="app_123",
        name="Updated Profile Name"
    )
    
    # Customer ID should remain unchanged
    assert result.customer_id == "cust_123"
    assert result.customer_id == sample_profile.customer_id


@pytest.mark.asyncio
async def test_deleting_customer_implications(customer_service, profile_service, mock_repository, sample_customer):
    """Test the implications of deleting a customer (profiles should be handled separately)."""
    # This test documents the expected behavior when a customer is deleted
    # In a real system, you might want to cascade delete profiles or prevent deletion
    
    mock_repository.delete_customer = AsyncMock()
    
    # Delete customer
    await customer_service.delete_customer("cust_123")
    
    # Verify delete was called
    mock_repository.delete_customer.assert_called_once_with("cust_123")
    
    # Note: In a production system, you would need to handle orphaned profiles
    # This could be done via:
    # 1. Cascade delete (delete all profiles when customer is deleted)
    # 2. Prevent deletion if profiles exist
    # 3. Mark profiles as inactive
    # This test documents that the service layer doesn't currently handle this


@pytest.mark.asyncio
async def test_profile_configuration_stored_with_customer_context(profile_service, mock_repository, sample_customer):
    """Test that profile configuration is stored with proper customer context."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    # Create profile with specific configuration
    profile = ApplicationProfile(
        id="app_123",
        customer_id="cust_123",
        name="Test Profile",
        type="chatbot",
        connection_config=ConnectionConfig(
            endpoint="https://api.example.com",
            timeout=60,
            retries=5,
            authentication={"type": "bearer", "token": "secret"},
            custom_headers={"X-Customer-ID": "cust_123"}
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_repository.create_application_profile = AsyncMock(return_value=profile)
    
    result = await profile_service.create_application_profile(
        customer_id="cust_123",
        name="Test Profile",
        app_type="chatbot",
        endpoint="https://api.example.com",
        timeout=60,
        retries=5,
        authentication={"type": "bearer", "token": "secret"},
        custom_headers={"X-Customer-ID": "cust_123"}
    )
    
    # Verify all configuration is stored with customer context
    assert result.customer_id == "cust_123"
    assert str(result.connection_config.endpoint).startswith("https://api.example.com")
    assert result.connection_config.timeout == 60
    assert result.connection_config.retries == 5
    assert result.connection_config.authentication is not None
    assert result.connection_config.custom_headers is not None
