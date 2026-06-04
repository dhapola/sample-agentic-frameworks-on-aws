"""Dataset management service.

Provides business logic for dataset CRUD operations with tenant isolation.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings
from app.database.repository import DataRepository
from app.models.dataset import Dataset
from app.models.test_case import TestCase

logger = logging.getLogger(__name__)


class DatasetService:
    """
    Service for managing datasets with tenant isolation.
    
    Handles dataset creation, retrieval, updates, and deletion
    with validation logic and customer_id enforcement.
    """
    
    def __init__(self, repository: DataRepository):
        """
        Initialize dataset service.
        
        Args:
            repository: Data repository for database operations
        """
        self._repository = repository
    
    async def create_dataset(
        self,
        customer_id: str,
        application_profile_id: str,
        name: str,
        description: str,
        file_path: str,
        test_cases: List[TestCase]
    ) -> Dataset:
        """
        Create a new dataset for a customer with CSV file.
        
        Args:
            customer_id: Customer ID for tenant isolation
            application_profile_id: Application profile ID
            name: Dataset name
            description: Dataset description
            file_path: Path to the uploaded CSV file
            test_cases: Parsed test cases from CSV
            
        Returns:
            Created dataset
            
        Raises:
            ValueError: If validation fails or dataset already exists
            RuntimeError: If database operation fails
        """
        # Validate inputs
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        if not application_profile_id or not application_profile_id.strip():
            raise ValueError("Application profile ID is required")
        
        if not name or not name.strip():
            raise ValueError("Dataset name is required")
        
        if not file_path or not file_path.strip():
            raise ValueError("File path is required")
        
        # Generate dataset ID
        dataset_id = f"dataset_{uuid.uuid4().hex[:12]}"
        
        # Create dataset object
        dataset = Dataset(
            id=dataset_id,
            customer_id=customer_id.strip(),
            application_profile_id=application_profile_id.strip(),
            name=name.strip(),
            description=description.strip() if description else "",
            file_path=file_path,
            test_cases=test_cases,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        created_dataset = await self._repository.create_dataset(dataset)
        
        logger.info(f"Created dataset: {created_dataset.id} for customer: {customer_id}")
        return created_dataset
    
    async def save_dataset_file(
        self,
        customer_id: str,
        filename: str,
        content: bytes
    ) -> str:
        """
        Save uploaded CSV file to disk.
        
        Args:
            customer_id: Customer ID for tenant isolation
            filename: Original filename
            content: File content as bytes
            
        Returns:
            Relative file path where file was saved
            
        Raises:
            RuntimeError: If file save fails
        """
        try:
            # Create customer-specific directory
            customer_dir = os.path.join(settings.upload_dir, customer_id)
            os.makedirs(customer_dir, exist_ok=True)
            
            # Generate unique filename
            file_id = uuid.uuid4().hex[:12]
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{file_id}{file_extension}"
            
            # Full file path
            file_path = os.path.join(customer_dir, unique_filename)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Return relative path
            relative_path = os.path.join(customer_id, unique_filename)
            logger.info(f"Saved dataset file: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"Failed to save dataset file: {str(e)}")
            raise RuntimeError(f"Failed to save file: {str(e)}")
    
    async def get_dataset_file_path(self, dataset_id: str, customer_id: str) -> str:
        """
        Get the full file path for a dataset's CSV file.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            
        Returns:
            Full file path
            
        Raises:
            ValueError: If dataset not found
        """
        dataset = await self.get_dataset(dataset_id, customer_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found")
        
        return os.path.join(settings.upload_dir, dataset.file_path)
    
    async def get_dataset(self, dataset_id: str, customer_id: str) -> Optional[Dataset]:
        """
        Get dataset by ID with tenant check.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            
        Returns:
            Dataset if found and belongs to customer, None otherwise
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If database operation fails
        """
        if not dataset_id or not dataset_id.strip():
            raise ValueError("Dataset ID is required")
        
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        return await self._repository.get_dataset_by_id(
            dataset_id.strip(),
            customer_id.strip()
        )
    
    async def get_datasets_by_customer(self, customer_id: str) -> List[Dataset]:
        """
        Get all datasets for a customer.
        
        Args:
            customer_id: Customer ID for tenant isolation
            
        Returns:
            List of datasets for the customer
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If database operation fails
        """
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        return await self._repository.get_datasets(customer_id.strip())
    
    async def update_dataset(
        self,
        dataset_id: str,
        customer_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dataset:
        """
        Update dataset information.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            name: Optional new dataset name
            description: Optional new dataset description
            
        Returns:
            Updated dataset
            
        Raises:
            ValueError: If validation fails or dataset not found
            RuntimeError: If database operation fails
        """
        if not dataset_id or not dataset_id.strip():
            raise ValueError("Dataset ID is required")
        
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        # Build updates dictionary
        updates: Dict[str, Any] = {}
        
        if name is not None:
            if not name.strip():
                raise ValueError("Dataset name cannot be empty")
            updates["name"] = name.strip()
        
        if description is not None:
            updates["description"] = description.strip() if description else ""
        
        if not updates:
            raise ValueError("No updates provided")
        
        # Update in database
        updated_dataset = await self._repository.update_dataset(
            dataset_id.strip(),
            customer_id.strip(),
            updates
        )
        
        logger.info(f"Updated dataset: {dataset_id}")
        return updated_dataset
    
    async def delete_dataset(self, dataset_id: str, customer_id: str) -> None:
        """
        Delete dataset with tenant check.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            
        Raises:
            ValueError: If dataset not found or doesn't belong to customer
            RuntimeError: If database operation fails
        """
        if not dataset_id or not dataset_id.strip():
            raise ValueError("Dataset ID is required")
        
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        await self._repository.delete_dataset(
            dataset_id.strip(),
            customer_id.strip()
        )
        
        logger.info(f"Deleted dataset: {dataset_id}")
    
    async def add_test_case(
        self,
        dataset_id: str,
        customer_id: str,
        input_text: str,
        expected_output: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TestCase:
        """
        Add a test case to a dataset.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            input_text: Test case input
            expected_output: Optional expected output
            metadata: Optional test case metadata
            
        Returns:
            Created test case
            
        Raises:
            ValueError: If validation fails or dataset not found
            RuntimeError: If database operation fails
        """
        if not dataset_id or not dataset_id.strip():
            raise ValueError("Dataset ID is required")
        
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        if not input_text or not input_text.strip():
            raise ValueError("Test case input is required")
        
        # Get existing dataset
        dataset = await self.get_dataset(dataset_id.strip(), customer_id.strip())
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found for customer {customer_id}")
        
        # Generate test case ID
        test_case_id = f"tc_{uuid.uuid4().hex[:12]}"
        
        # Create test case
        test_case = TestCase(
            id=test_case_id,
            input=input_text.strip(),
            expected_output=expected_output,
            metadata=metadata
        )
        
        # Add to dataset's test cases
        updated_test_cases = dataset.test_cases + [test_case]
        
        # Update dataset
        await self._repository.update_dataset(
            dataset_id.strip(),
            customer_id.strip(),
            {"test_cases": [tc.model_dump() for tc in updated_test_cases]}
        )
        
        logger.info(f"Added test case {test_case_id} to dataset {dataset_id}")
        return test_case
    
    async def update_test_case(
        self,
        dataset_id: str,
        customer_id: str,
        test_case_id: str,
        input_text: Optional[str] = None,
        expected_output: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TestCase:
        """
        Update a test case in a dataset.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            test_case_id: Test case ID
            input_text: Optional new input text
            expected_output: Optional new expected output
            metadata: Optional new metadata
            
        Returns:
            Updated test case
            
        Raises:
            ValueError: If validation fails or test case not found
            RuntimeError: If database operation fails
        """
        if not dataset_id or not dataset_id.strip():
            raise ValueError("Dataset ID is required")
        
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        if not test_case_id or not test_case_id.strip():
            raise ValueError("Test case ID is required")
        
        # Get existing dataset
        dataset = await self.get_dataset(dataset_id.strip(), customer_id.strip())
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found for customer {customer_id}")
        
        # Find test case
        test_case_index = None
        for i, tc in enumerate(dataset.test_cases):
            if tc.id == test_case_id.strip():
                test_case_index = i
                break
        
        if test_case_index is None:
            raise ValueError(f"Test case with ID {test_case_id} not found in dataset {dataset_id}")
        
        # Update test case fields
        test_case = dataset.test_cases[test_case_index]
        
        if input_text is not None:
            if not input_text.strip():
                raise ValueError("Test case input cannot be empty")
            test_case.input = input_text.strip()
        
        if expected_output is not None:
            test_case.expected_output = expected_output
        
        if metadata is not None:
            test_case.metadata = metadata
        
        # Update dataset
        dataset.test_cases[test_case_index] = test_case
        await self._repository.update_dataset(
            dataset_id.strip(),
            customer_id.strip(),
            {"test_cases": [tc.model_dump() for tc in dataset.test_cases]}
        )
        
        logger.info(f"Updated test case {test_case_id} in dataset {dataset_id}")
        return test_case
    
    async def delete_test_case(
        self,
        dataset_id: str,
        customer_id: str,
        test_case_id: str
    ) -> None:
        """
        Delete a test case from a dataset.
        
        Args:
            dataset_id: Dataset ID
            customer_id: Customer ID for tenant isolation
            test_case_id: Test case ID
            
        Raises:
            ValueError: If test case not found
            RuntimeError: If database operation fails
        """
        if not dataset_id or not dataset_id.strip():
            raise ValueError("Dataset ID is required")
        
        if not customer_id or not customer_id.strip():
            raise ValueError("Customer ID is required")
        
        if not test_case_id or not test_case_id.strip():
            raise ValueError("Test case ID is required")
        
        # Get existing dataset
        dataset = await self.get_dataset(dataset_id.strip(), customer_id.strip())
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found for customer {customer_id}")
        
        # Find and remove test case
        test_case_found = False
        updated_test_cases = []
        for tc in dataset.test_cases:
            if tc.id == test_case_id.strip():
                test_case_found = True
            else:
                updated_test_cases.append(tc)
        
        if not test_case_found:
            raise ValueError(f"Test case with ID {test_case_id} not found in dataset {dataset_id}")
        
        # Update dataset
        await self._repository.update_dataset(
            dataset_id.strip(),
            customer_id.strip(),
            {"test_cases": [tc.model_dump() for tc in updated_test_cases]}
        )
        
        logger.info(f"Deleted test case {test_case_id} from dataset {dataset_id}")
