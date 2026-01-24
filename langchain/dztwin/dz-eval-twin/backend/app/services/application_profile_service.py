"""Application profile management service.

Provides business logic for application profile CRUD operations.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.database.repository import DataRepository
from app.models.application_profile import ApplicationProfile, ApplicationType
from app.models.connection_config import ConnectionConfig
from app.utils.validation import validate_url, validate_phone_number

logger = logging.getLogger(__name__)


class ApplicationProfileService:
    """
    Service for managing application profiles.
    
    Handles application profile creation, retrieval, updates, and deletion
    with validation logic and customer linkage.
    """
    
    def __init__(self, repository: DataRepository):
        """
        Initialize application profile service.
        
        Args:
            repository: Data repository for database operations
        """
        self._repository = repository
    
    async def create_application_profile(
        self,
        customer_id: str,
        name: str,
        app_type: str,
        endpoint: str,
        timeout: int = 30,
        retries: int = 3,
        authentication: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> ApplicationProfile:
        """
        Create a new application profile.
        
        Args:
            customer_id: Customer ID this profile belongs to
            name: Profile name
            app_type: Application type (chatbot, rag, agent, workflow, custom)
            endpoint: Application endpoint URL
            timeout: Request timeout in seconds (1-300)
            retries: Number of retry attempts (0-10)
            authentication: Optional authentication configuration
            custom_headers: Optional custom HTTP headers
            
        Returns:
            Created application profile
            
        Raises:
            ValueError: If validation fails or profile already exists
            RuntimeError: If database operation fails
        """
        # Validate inputs
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        if not name or not name.strip():
            raise ValueError("Profile name is required")
        
        if not app_type or not app_type.strip():
            raise ValueError("Application type is required")
        
        # Validate application type
        valid_types = ["chatbot", "rag", "agent", "workflow", "custom"]
        if app_type.lower() not in valid_types:
            raise ValueError(f"Invalid application type. Must be one of: {', '.join(valid_types)}")
        
        if not endpoint or not endpoint.strip():
            raise ValueError("Endpoint is required")
        
        # Validate endpoint URL format
        validated_endpoint = validate_url(endpoint, "Endpoint")
        
        # Validate timeout
        if timeout < 1 or timeout > 300:
            raise ValueError("Timeout must be between 1 and 300 seconds")
        
        # Validate retries
        if retries < 0 or retries > 10:
            raise ValueError("Retries must be between 0 and 10")
        
        # Verify customer exists
        customer = await self._repository.get_customer_by_id(customer_id.strip())
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} not found")
        
        # Generate profile ID
        import uuid
        profile_id = f"app_{uuid.uuid4().hex[:12]}"
        
        # Create connection config
        connection_config = ConnectionConfig(
            endpoint=validated_endpoint,
            authentication=authentication,
            timeout=timeout,
            retries=retries,
            custom_headers=custom_headers
        )
        
        # Create application profile object
        profile = ApplicationProfile(
            id=profile_id,
            customer_id=customer_id.strip(),
            name=name.strip(),
            type=app_type.lower(),
            connection_config=connection_config,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        created_profile = await self._repository.create_application_profile(profile)
        
        logger.info(f"Created application profile: {created_profile.id} for customer: {customer_id}")
        return created_profile
    
    async def get_application_profile(self, profile_id: str) -> Optional[ApplicationProfile]:
        """
        Get application profile by ID.
        
        Args:
            profile_id: Application profile ID
            
        Returns:
            Application profile if found, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not profile_id or not profile_id.strip():
            raise ValueError("Profile ID is required")
        
        return await self._repository.get_application_profile_by_id(profile_id.strip())
    
    async def get_profiles_by_customer(self, customer_id: str) -> List[ApplicationProfile]:
        """
        Get all application profiles for a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            List of application profiles for the customer
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        return await self._repository.get_application_profiles(customer_id.strip())
    
    async def get_all_profiles(self) -> List[ApplicationProfile]:
        """
        Get all application profiles.
        
        Returns:
            List of all application profiles
            
        Raises:
            RuntimeError: If database operation fails
        """
        return await self._repository.get_application_profiles()
    
    async def update_application_profile(
        self,
        profile_id: str,
        name: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        authentication: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> ApplicationProfile:
        """
        Update application profile.
        
        Args:
            profile_id: Application profile ID
            name: Optional new profile name
            endpoint: Optional new endpoint URL
            timeout: Optional new timeout
            retries: Optional new retry count
            authentication: Optional new authentication config
            custom_headers: Optional new custom headers
            
        Returns:
            Updated application profile
            
        Raises:
            ValueError: If validation fails or profile not found
            RuntimeError: If database operation fails
        """
        if not profile_id or not profile_id.strip():
            raise ValueError("Profile ID is required")
        
        # Build updates dictionary
        updates: Dict[str, Any] = {}
        
        if name is not None:
            if not name.strip():
                raise ValueError("Profile name cannot be empty")
            updates["name"] = name.strip()
        
        # For connection config updates, we need to get the current profile first
        # and update the connection_config object
        if any(x is not None for x in [endpoint, timeout, retries, authentication, custom_headers]):
            # Get current profile
            current_profile = await self._repository.get_application_profile_by_id(profile_id.strip())
            if not current_profile:
                raise ValueError(f"Application profile with ID {profile_id} not found")
            
            # Create updated connection config
            config_dict = current_profile.connection_config.model_dump()
            
            if endpoint is not None:
                if not endpoint.strip():
                    raise ValueError("Endpoint cannot be empty")
                validated_endpoint = validate_url(endpoint, "Endpoint")
                config_dict["endpoint"] = validated_endpoint
            
            if timeout is not None:
                if timeout < 1 or timeout > 300:
                    raise ValueError("Timeout must be between 1 and 300 seconds")
                config_dict["timeout"] = timeout
            
            if retries is not None:
                if retries < 0 or retries > 10:
                    raise ValueError("Retries must be between 0 and 10")
                config_dict["retries"] = retries
            
            if authentication is not None:
                config_dict["authentication"] = authentication
            
            if custom_headers is not None:
                config_dict["custom_headers"] = custom_headers
            
            updates["connection_config"] = config_dict
        
        if not updates:
            raise ValueError("No updates provided")
        
        # Update in database
        updated_profile = await self._repository.update_application_profile(
            profile_id.strip(),
            updates
        )
        
        logger.info(f"Updated application profile: {profile_id}")
        return updated_profile
    
    async def delete_application_profile(self, profile_id: str) -> None:
        """
        Delete application profile.
        
        Args:
            profile_id: Application profile ID
            
        Raises:
            ValueError: If profile not found
            RuntimeError: If database operation fails
        """
        if not profile_id or not profile_id.strip():
            raise ValueError("Profile ID is required")
        
        await self._repository.delete_application_profile(profile_id.strip())
        
        logger.info(f"Deleted application profile: {profile_id}")
    
    async def validate_profile_exists(self, profile_id: str) -> bool:
        """
        Check if application profile exists.
        
        Args:
            profile_id: Application profile ID
            
        Returns:
            True if profile exists, False otherwise
        """
        if not profile_id or not profile_id.strip():
            return False
        
        profile = await self._repository.get_application_profile_by_id(profile_id.strip())
        return profile is not None
    
    async def validate_profile_belongs_to_customer(
        self,
        profile_id: str,
        customer_id: str
    ) -> bool:
        """
        Check if application profile belongs to a specific customer.
        
        Args:
            profile_id: Application profile ID
            customer_id: Customer ID
            
        Returns:
            True if profile belongs to customer, False otherwise
        """
        if not profile_id or not profile_id.strip():
            return False
        
        if not customer_id or not customer_id.strip():
            return False
        
        profile = await self._repository.get_application_profile_by_id(profile_id.strip())
        if not profile:
            return False
        
        return profile.customer_id == customer_id.strip()
