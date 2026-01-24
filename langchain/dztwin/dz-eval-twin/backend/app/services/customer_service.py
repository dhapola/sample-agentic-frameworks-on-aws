"""Customer management service.

Provides business logic for customer CRUD operations.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.database.repository import DataRepository
from app.models.customer import Customer
from app.utils.validation import validate_phone_number

logger = logging.getLogger(__name__)


class CustomerService:
    """
    Service for managing customers.
    
    Handles customer creation, retrieval, updates, and deletion
    with validation logic.
    """
    
    def __init__(self, repository: DataRepository):
        """
        Initialize customer service.
        
        Args:
            repository: Data repository for database operations
        """
        self._repository = repository
    
    async def create_customer(
        self,
        name: str,
        contact_email: str,
        contact_phone: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> Customer:
        """
        Create a new customer.
        
        Args:
            name: Customer name
            contact_email: Customer contact email
            contact_phone: Optional customer contact phone
            configuration: Optional customer configuration settings
            
        Returns:
            Created customer
            
        Raises:
            ValueError: If validation fails or customer already exists
            RuntimeError: If database operation fails
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Customer name is required")
        
        if not contact_email or not contact_email.strip():
            raise ValueError("Customer contact email is required")
        
        # Basic email validation
        if "@" not in contact_email or "." not in contact_email:
            raise ValueError("Invalid email format")
        
        # Validate phone number if provided
        validated_phone = validate_phone_number(contact_phone, "Contact phone")
        
        # Generate customer ID
        import uuid
        customer_id = f"cust_{uuid.uuid4().hex[:12]}"
        
        # Create customer object
        customer = Customer(
            id=customer_id,
            name=name.strip(),
            contact_email=contact_email.strip(),
            contact_phone=validated_phone,
            configuration=configuration or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        created_customer = await self._repository.create_customer(customer)
        
        logger.info(f"Created customer: {created_customer.id}")
        return created_customer
    
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """
        Get customer by ID.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer if found, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        return await self._repository.get_customer_by_id(customer_id.strip())
    
    async def get_all_customers(self) -> List[Customer]:
        """
        Get all customers.
        
        Returns:
            List of all customers
            
        Raises:
            RuntimeError: If database operation fails
        """
        return await self._repository.get_customers()
    
    async def update_customer(
        self,
        customer_id: str,
        name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> Customer:
        """
        Update customer information.
        
        Args:
            customer_id: Customer ID
            name: Optional new customer name
            contact_email: Optional new contact email
            contact_phone: Optional new contact phone
            configuration: Optional new configuration settings
            
        Returns:
            Updated customer
            
        Raises:
            ValueError: If validation fails or customer not found
            RuntimeError: If database operation fails
        """
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        # Build updates dictionary
        updates: Dict[str, Any] = {}
        
        if name is not None:
            if not name.strip():
                raise ValueError("Customer name cannot be empty")
            updates["name"] = name.strip()
        
        if contact_email is not None:
            if not contact_email.strip():
                raise ValueError("Contact email cannot be empty")
            if "@" not in contact_email or "." not in contact_email:
                raise ValueError("Invalid email format")
            updates["contact_email"] = contact_email.strip()
        
        if contact_phone is not None:
            validated_phone = validate_phone_number(contact_phone, "Contact phone")
            updates["contact_phone"] = validated_phone
        
        if configuration is not None:
            updates["configuration"] = configuration
        
        if not updates:
            raise ValueError("No updates provided")
        
        # Update in database
        updated_customer = await self._repository.update_customer(
            customer_id.strip(),
            updates
        )
        
        logger.info(f"Updated customer: {customer_id}")
        return updated_customer
    
    async def delete_customer(self, customer_id: str) -> None:
        """
        Delete customer.
        
        Args:
            customer_id: Customer ID
            
        Raises:
            ValueError: If customer not found
            RuntimeError: If database operation fails
        """
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        await self._repository.delete_customer(customer_id.strip())
        
        logger.info(f"Deleted customer: {customer_id}")
    
    async def validate_customer_exists(self, customer_id: str) -> bool:
        """
        Check if customer exists.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            True if customer exists, False otherwise
        """
        if not customer_id or not customer_id.strip():
            return False
        
        customer = await self._repository.get_customer_by_id(customer_id.strip())
        return customer is not None
