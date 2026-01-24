"""Unit tests for CustomerService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.customer_service import CustomerService
from app.models.customer import Customer


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return MagicMock()


@pytest.fixture
def customer_service(mock_repository):
    """Create a CustomerService with mock repository."""
    return CustomerService(mock_repository)


@pytest.fixture
def sample_customer():
    """Create a sample customer."""
    return Customer(
        id="cust_123",
        name="Test Customer",
        contact_email="test@example.com",
        contact_phone="+1-555-0100",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# ==================== Create Customer Tests ====================

@pytest.mark.asyncio
async def test_create_customer_success(customer_service, mock_repository, sample_customer):
    """Test successful customer creation."""
    mock_repository.create_customer = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.create_customer(
        name="Test Customer",
        contact_email="test@example.com",
        contact_phone="+1-555-0100"
    )
    
    assert result.name == "Test Customer"
    assert result.contact_email == "test@example.com"
    mock_repository.create_customer.assert_called_once()


@pytest.mark.asyncio
async def test_create_customer_empty_name(customer_service):
    """Test creating customer with empty name fails."""
    with pytest.raises(ValueError, match="Customer name is required"):
        await customer_service.create_customer(
            name="",
            contact_email="test@example.com"
        )


@pytest.mark.asyncio
async def test_create_customer_whitespace_name(customer_service):
    """Test creating customer with whitespace-only name fails."""
    with pytest.raises(ValueError, match="Customer name is required"):
        await customer_service.create_customer(
            name="   ",
            contact_email="test@example.com"
        )


@pytest.mark.asyncio
async def test_create_customer_empty_email(customer_service):
    """Test creating customer with empty email fails."""
    with pytest.raises(ValueError, match="Customer contact email is required"):
        await customer_service.create_customer(
            name="Test Customer",
            contact_email=""
        )


@pytest.mark.asyncio
async def test_create_customer_invalid_email(customer_service):
    """Test creating customer with invalid email fails."""
    with pytest.raises(ValueError, match="Invalid email format"):
        await customer_service.create_customer(
            name="Test Customer",
            contact_email="invalid-email"
        )


@pytest.mark.asyncio
async def test_create_customer_no_at_symbol(customer_service):
    """Test creating customer with email missing @ symbol fails."""
    with pytest.raises(ValueError, match="Invalid email format"):
        await customer_service.create_customer(
            name="Test Customer",
            contact_email="test.example.com"
        )


@pytest.mark.asyncio
async def test_create_customer_with_configuration(customer_service, mock_repository, sample_customer):
    """Test creating customer with configuration."""
    sample_customer.configuration = {"theme": "dark", "notifications": True}
    mock_repository.create_customer = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.create_customer(
        name="Test Customer",
        contact_email="test@example.com",
        configuration={"theme": "dark", "notifications": True}
    )
    
    assert result.configuration == {"theme": "dark", "notifications": True}


@pytest.mark.asyncio
async def test_create_customer_trims_whitespace(customer_service, mock_repository, sample_customer):
    """Test that customer creation trims whitespace from inputs."""
    mock_repository.create_customer = AsyncMock(return_value=sample_customer)
    
    await customer_service.create_customer(
        name="  Test Customer  ",
        contact_email="  test@example.com  ",
        contact_phone="  +1-555-0100  "
    )
    
    # Verify the repository was called with trimmed values
    call_args = mock_repository.create_customer.call_args[0][0]
    assert call_args.name == "Test Customer"
    assert call_args.contact_email == "test@example.com"
    assert call_args.contact_phone == "+1-555-0100"


# ==================== Get Customer Tests ====================

@pytest.mark.asyncio
async def test_get_customer_success(customer_service, mock_repository, sample_customer):
    """Test successful customer retrieval."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.get_customer("cust_123")
    
    assert result is not None
    assert result.id == "cust_123"
    mock_repository.get_customer_by_id.assert_called_once_with("cust_123")


@pytest.mark.asyncio
async def test_get_customer_not_found(customer_service, mock_repository):
    """Test getting non-existent customer returns None."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=None)
    
    result = await customer_service.get_customer("nonexistent")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_customer_empty_id(customer_service):
    """Test getting customer with empty ID fails."""
    with pytest.raises(ValueError, match="Customer ID is required"):
        await customer_service.get_customer("")


@pytest.mark.asyncio
async def test_get_customer_trims_whitespace(customer_service, mock_repository, sample_customer):
    """Test that get customer trims whitespace from ID."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    await customer_service.get_customer("  cust_123  ")
    
    mock_repository.get_customer_by_id.assert_called_once_with("cust_123")


# ==================== Get All Customers Tests ====================

@pytest.mark.asyncio
async def test_get_all_customers_success(customer_service, mock_repository):
    """Test getting all customers."""
    customers = [
        Customer(
            id="cust_1",
            name="Customer 1",
            contact_email="test1@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Customer(
            id="cust_2",
            name="Customer 2",
            contact_email="test2@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    mock_repository.get_customers = AsyncMock(return_value=customers)
    
    result = await customer_service.get_all_customers()
    
    assert len(result) == 2
    assert result[0].id == "cust_1"
    assert result[1].id == "cust_2"


@pytest.mark.asyncio
async def test_get_all_customers_empty(customer_service, mock_repository):
    """Test getting all customers when none exist."""
    mock_repository.get_customers = AsyncMock(return_value=[])
    
    result = await customer_service.get_all_customers()
    
    assert len(result) == 0


# ==================== Update Customer Tests ====================

@pytest.mark.asyncio
async def test_update_customer_name(customer_service, mock_repository, sample_customer):
    """Test updating customer name."""
    sample_customer.name = "Updated Customer"
    mock_repository.update_customer = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.update_customer(
        customer_id="cust_123",
        name="Updated Customer"
    )
    
    assert result.name == "Updated Customer"
    mock_repository.update_customer.assert_called_once()


@pytest.mark.asyncio
async def test_update_customer_email(customer_service, mock_repository, sample_customer):
    """Test updating customer email."""
    sample_customer.contact_email = "updated@example.com"
    mock_repository.update_customer = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.update_customer(
        customer_id="cust_123",
        contact_email="updated@example.com"
    )
    
    assert result.contact_email == "updated@example.com"


@pytest.mark.asyncio
async def test_update_customer_empty_name(customer_service):
    """Test updating customer with empty name fails."""
    with pytest.raises(ValueError, match="Customer name cannot be empty"):
        await customer_service.update_customer(
            customer_id="cust_123",
            name=""
        )


@pytest.mark.asyncio
async def test_update_customer_invalid_email(customer_service):
    """Test updating customer with invalid email fails."""
    with pytest.raises(ValueError, match="Invalid email format"):
        await customer_service.update_customer(
            customer_id="cust_123",
            contact_email="invalid-email"
        )


@pytest.mark.asyncio
async def test_update_customer_no_updates(customer_service):
    """Test updating customer with no updates fails."""
    with pytest.raises(ValueError, match="No updates provided"):
        await customer_service.update_customer(customer_id="cust_123")


@pytest.mark.asyncio
async def test_update_customer_empty_id(customer_service):
    """Test updating customer with empty ID fails."""
    with pytest.raises(ValueError, match="Customer ID is required"):
        await customer_service.update_customer(
            customer_id="",
            name="Updated"
        )


@pytest.mark.asyncio
async def test_update_customer_configuration(customer_service, mock_repository, sample_customer):
    """Test updating customer configuration."""
    sample_customer.configuration = {"new_setting": "value"}
    mock_repository.update_customer = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.update_customer(
        customer_id="cust_123",
        configuration={"new_setting": "value"}
    )
    
    assert result.configuration == {"new_setting": "value"}


# ==================== Delete Customer Tests ====================

@pytest.mark.asyncio
async def test_delete_customer_success(customer_service, mock_repository):
    """Test successful customer deletion."""
    mock_repository.delete_customer = AsyncMock()
    
    await customer_service.delete_customer("cust_123")
    
    mock_repository.delete_customer.assert_called_once_with("cust_123")


@pytest.mark.asyncio
async def test_delete_customer_empty_id(customer_service):
    """Test deleting customer with empty ID fails."""
    with pytest.raises(ValueError, match="Customer ID is required"):
        await customer_service.delete_customer("")


@pytest.mark.asyncio
async def test_delete_customer_not_found(customer_service, mock_repository):
    """Test deleting non-existent customer raises error."""
    mock_repository.delete_customer = AsyncMock(side_effect=ValueError("not found"))
    
    with pytest.raises(ValueError, match="not found"):
        await customer_service.delete_customer("nonexistent")


# ==================== Validate Customer Exists Tests ====================

@pytest.mark.asyncio
async def test_validate_customer_exists_true(customer_service, mock_repository, sample_customer):
    """Test validating existing customer returns True."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=sample_customer)
    
    result = await customer_service.validate_customer_exists("cust_123")
    
    assert result is True


@pytest.mark.asyncio
async def test_validate_customer_exists_false(customer_service, mock_repository):
    """Test validating non-existent customer returns False."""
    mock_repository.get_customer_by_id = AsyncMock(return_value=None)
    
    result = await customer_service.validate_customer_exists("nonexistent")
    
    assert result is False


@pytest.mark.asyncio
async def test_validate_customer_exists_empty_id(customer_service):
    """Test validating customer with empty ID returns False."""
    result = await customer_service.validate_customer_exists("")
    
    assert result is False
