"""Data repository for MongoDB operations with tenant isolation."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.application_profile import ApplicationProfile
from app.models.customer import Customer
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.response import Response

logger = logging.getLogger(__name__)


class DataRepository:
    """
    Repository for data persistence operations with tenant isolation.
    
    All tenant-scoped operations (datasets, evaluation runs) enforce
    customer_id filtering to ensure complete data isolation.
    """

    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize repository with database connection.
        
        Args:
            database: MongoDB database instance
        """
        self._db = database

    # ==================== Customer Operations ====================

    async def create_customer(self, customer: Customer) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer: Customer object to create
            
        Returns:
            Created customer with generated ID
            
        Raises:
            ValueError: If customer with same ID already exists
            RuntimeError: If database operation fails
        """
        try:
            customer_dict = customer.model_dump()
            customer_dict["_id"] = customer.id
            customer_dict.pop("id", None)
            
            result = await self._db.customers.insert_one(customer_dict)
            logger.info(f"Created customer: {customer.id}")
            
            return customer
            
        except DuplicateKeyError:
            raise ValueError(f"Customer with ID {customer.id} already exists")
        except PyMongoError as e:
            logger.error(f"Failed to create customer: {e}")
            raise RuntimeError(f"Database error creating customer: {e}") from e

    async def get_customers(self) -> List[Customer]:
        """
        Get all customers.
        
        Returns:
            List of all customers
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            cursor = self._db.customers.find()
            customers = []
            
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                customers.append(Customer(**doc))
            
            return customers
            
        except PyMongoError as e:
            logger.error(f"Failed to get customers: {e}")
            raise RuntimeError(f"Database error retrieving customers: {e}") from e

    async def get_customer_by_id(self, id: str) -> Optional[Customer]:
        """
        Get customer by ID.
        
        Args:
            id: Customer ID
            
        Returns:
            Customer if found, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            doc = await self._db.customers.find_one({"_id": id})
            
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return Customer(**doc)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Failed to get customer {id}: {e}")
            raise RuntimeError(f"Database error retrieving customer: {e}") from e

    async def update_customer(self, id: str, updates: Dict[str, Any]) -> Customer:
        """
        Update customer.
        
        Args:
            id: Customer ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated customer
            
        Raises:
            ValueError: If customer not found
            RuntimeError: If database operation fails
        """
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            result = await self._db.customers.find_one_and_update(
                {"_id": id},
                {"$set": updates},
                return_document=True
            )
            
            if not result:
                raise ValueError(f"Customer with ID {id} not found")
            
            result["id"] = str(result.pop("_id"))
            logger.info(f"Updated customer: {id}")
            
            return Customer(**result)
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to update customer {id}: {e}")
            raise RuntimeError(f"Database error updating customer: {e}") from e

    async def delete_customer(self, id: str) -> None:
        """
        Delete customer.
        
        Args:
            id: Customer ID
            
        Raises:
            ValueError: If customer not found
            RuntimeError: If database operation fails
        """
        try:
            result = await self._db.customers.delete_one({"_id": id})
            
            if result.deleted_count == 0:
                raise ValueError(f"Customer with ID {id} not found")
            
            logger.info(f"Deleted customer: {id}")
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to delete customer {id}: {e}")
            raise RuntimeError(f"Database error deleting customer: {e}") from e

    # ==================== Application Profile Operations ====================

    async def create_application_profile(self, profile: ApplicationProfile) -> ApplicationProfile:
        """
        Create a new application profile.
        
        Args:
            profile: ApplicationProfile object to create
            
        Returns:
            Created application profile
            
        Raises:
            ValueError: If profile with same ID already exists
            RuntimeError: If database operation fails
        """
        try:
            profile_dict = profile.model_dump()
            profile_dict["_id"] = profile.id
            profile_dict.pop("id", None)
            
            # Convert snake_case to camelCase for MongoDB
            profile_dict["customerId"] = profile_dict.pop("customer_id")
            profile_dict["connectionConfig"] = profile_dict.pop("connection_config")
            
            # Convert nested Pydantic models to dicts
            if isinstance(profile_dict["connectionConfig"], dict):
                pass  # Already a dict from model_dump()
            else:
                profile_dict["connectionConfig"] = dict(profile_dict["connectionConfig"])
            
            result = await self._db.applicationProfiles.insert_one(profile_dict)
            logger.info(f"Created application profile: {profile.id} for customer: {profile.customer_id}")
            
            return profile
            
        except DuplicateKeyError:
            raise ValueError(f"Application profile with ID {profile.id} already exists")
        except PyMongoError as e:
            logger.error(f"Failed to create application profile: {e}")
            raise RuntimeError(f"Database error creating application profile: {e}") from e

    async def get_application_profiles(self, customer_id: Optional[str] = None) -> List[ApplicationProfile]:
        """
        Get application profiles, optionally filtered by customer.
        
        Args:
            customer_id: Optional customer ID to filter by
            
        Returns:
            List of application profiles
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            query = {}
            if customer_id:
                query["customerId"] = customer_id
            
            cursor = self._db.applicationProfiles.find(query)
            profiles = []
            
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                # Convert camelCase to snake_case for Pydantic
                doc["customer_id"] = doc.pop("customerId")
                doc["connection_config"] = doc.pop("connectionConfig")
                profiles.append(ApplicationProfile(**doc))
            
            return profiles
            
        except PyMongoError as e:
            logger.error(f"Failed to get application profiles: {e}")
            raise RuntimeError(f"Database error retrieving application profiles: {e}") from e

    async def get_application_profile_by_id(self, id: str) -> Optional[ApplicationProfile]:
        """
        Get application profile by ID.
        
        Args:
            id: Application profile ID
            
        Returns:
            ApplicationProfile if found, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            doc = await self._db.applicationProfiles.find_one({"_id": id})
            
            if doc:
                doc["id"] = str(doc.pop("_id"))
                doc["customer_id"] = doc.pop("customerId")
                doc["connection_config"] = doc.pop("connectionConfig")
                return ApplicationProfile(**doc)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Failed to get application profile {id}: {e}")
            raise RuntimeError(f"Database error retrieving application profile: {e}") from e

    async def update_application_profile(self, id: str, updates: Dict[str, Any]) -> ApplicationProfile:
        """
        Update application profile.
        
        Args:
            id: Application profile ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated application profile
            
        Raises:
            ValueError: If profile not found
            RuntimeError: If database operation fails
        """
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            # Convert snake_case to camelCase for MongoDB
            if "customer_id" in updates:
                updates["customerId"] = updates.pop("customer_id")
            if "connection_config" in updates:
                updates["connectionConfig"] = updates.pop("connection_config")
            
            result = await self._db.applicationProfiles.find_one_and_update(
                {"_id": id},
                {"$set": updates},
                return_document=True
            )
            
            if not result:
                raise ValueError(f"Application profile with ID {id} not found")
            
            result["id"] = str(result.pop("_id"))
            result["customer_id"] = result.pop("customerId")
            result["connection_config"] = result.pop("connectionConfig")
            logger.info(f"Updated application profile: {id}")
            
            return ApplicationProfile(**result)
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to update application profile {id}: {e}")
            raise RuntimeError(f"Database error updating application profile: {e}") from e

    async def delete_application_profile(self, id: str) -> None:
        """
        Delete application profile.
        
        Args:
            id: Application profile ID
            
        Raises:
            ValueError: If profile not found
            RuntimeError: If database operation fails
        """
        try:
            result = await self._db.applicationProfiles.delete_one({"_id": id})
            
            if result.deleted_count == 0:
                raise ValueError(f"Application profile with ID {id} not found")
            
            logger.info(f"Deleted application profile: {id}")
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to delete application profile {id}: {e}")
            raise RuntimeError(f"Database error deleting application profile: {e}") from e

    # ==================== Dataset Operations (Tenant-Scoped) ====================

    async def create_dataset(self, dataset: Dataset) -> Dataset:
        """
        Create a new dataset.
        
        Args:
            dataset: Dataset object to create
            
        Returns:
            Created dataset
            
        Raises:
            ValueError: If dataset with same ID already exists
            RuntimeError: If database operation fails
        """
        try:
            dataset_dict = dataset.model_dump()
            dataset_dict["_id"] = dataset.id
            dataset_dict.pop("id", None)
            
            # Convert snake_case to camelCase for MongoDB
            dataset_dict["customerId"] = dataset_dict.pop("customer_id")
            dataset_dict["testCases"] = dataset_dict.pop("test_cases")
            
            result = await self._db.datasets.insert_one(dataset_dict)
            logger.info(f"Created dataset: {dataset.id} for customer: {dataset.customer_id}")
            
            return dataset
            
        except DuplicateKeyError:
            raise ValueError(f"Dataset with ID {dataset.id} already exists")
        except PyMongoError as e:
            logger.error(f"Failed to create dataset: {e}")
            raise RuntimeError(f"Database error creating dataset: {e}") from e

    async def get_datasets(self, customer_id: str) -> List[Dataset]:
        """
        Get all datasets for a customer (tenant-scoped).
        
        Args:
            customer_id: Customer ID for tenant isolation
            
        Returns:
            List of datasets for the customer
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            cursor = self._db.datasets.find({"customerId": customer_id})
            datasets = []
            
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                doc["customer_id"] = doc.pop("customerId")
                doc["test_cases"] = doc.pop("testCases", [])
                datasets.append(Dataset(**doc))
            
            return datasets
            
        except PyMongoError as e:
            logger.error(f"Failed to get datasets for customer {customer_id}: {e}")
            raise RuntimeError(f"Database error retrieving datasets: {e}") from e

    async def get_dataset_by_id(self, id: str, customer_id: str) -> Optional[Dataset]:
        """
        Get dataset by ID with tenant check.
        
        Args:
            id: Dataset ID
            customer_id: Customer ID for tenant isolation
            
        Returns:
            Dataset if found and belongs to customer, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            doc = await self._db.datasets.find_one({"_id": id, "customerId": customer_id})
            
            if doc:
                doc["id"] = str(doc.pop("_id"))
                doc["customer_id"] = doc.pop("customerId")
                doc["test_cases"] = doc.pop("testCases", [])
                return Dataset(**doc)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Failed to get dataset {id}: {e}")
            raise RuntimeError(f"Database error retrieving dataset: {e}") from e

    async def update_dataset(self, id: str, customer_id: str, updates: Dict[str, Any]) -> Dataset:
        """
        Update dataset with tenant check.
        
        Args:
            id: Dataset ID
            customer_id: Customer ID for tenant isolation
            updates: Dictionary of fields to update
            
        Returns:
            Updated dataset
            
        Raises:
            ValueError: If dataset not found or doesn't belong to customer
            RuntimeError: If database operation fails
        """
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            # Convert snake_case to camelCase for MongoDB
            if "test_cases" in updates:
                updates["testCases"] = updates.pop("test_cases")
            
            result = await self._db.datasets.find_one_and_update(
                {"_id": id, "customerId": customer_id},
                {"$set": updates},
                return_document=True
            )
            
            if not result:
                raise ValueError(f"Dataset with ID {id} not found for customer {customer_id}")
            
            result["id"] = str(result.pop("_id"))
            result["customer_id"] = result.pop("customerId")
            result["test_cases"] = result.pop("testCases", [])
            logger.info(f"Updated dataset: {id}")
            
            return Dataset(**result)
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to update dataset {id}: {e}")
            raise RuntimeError(f"Database error updating dataset: {e}") from e

    async def delete_dataset(self, id: str, customer_id: str) -> None:
        """
        Delete dataset with tenant check.
        
        Args:
            id: Dataset ID
            customer_id: Customer ID for tenant isolation
            
        Raises:
            ValueError: If dataset not found or doesn't belong to customer
            RuntimeError: If database operation fails
        """
        try:
            result = await self._db.datasets.delete_one({"_id": id, "customerId": customer_id})
            
            if result.deleted_count == 0:
                raise ValueError(f"Dataset with ID {id} not found for customer {customer_id}")
            
            logger.info(f"Deleted dataset: {id}")
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to delete dataset {id}: {e}")
            raise RuntimeError(f"Database error deleting dataset: {e}") from e

    # ==================== Evaluation Run Operations (Tenant-Scoped) ====================

    async def create_evaluation_run(self, run: EvaluationRun) -> EvaluationRun:
        """
        Create a new evaluation run.
        
        Args:
            run: EvaluationRun object to create
            
        Returns:
            Created evaluation run
            
        Raises:
            ValueError: If run with same ID already exists
            RuntimeError: If database operation fails
        """
        try:
            run_dict = run.model_dump()
            run_dict["_id"] = run.id
            run_dict.pop("id", None)
            
            # Convert snake_case to camelCase for MongoDB
            run_dict["customerId"] = run_dict.pop("customer_id")
            run_dict["datasetId"] = run_dict.pop("dataset_id")
            run_dict["applicationProfileId"] = run_dict.pop("application_profile_id")
            run_dict["startTime"] = run_dict.pop("start_time")
            if "end_time" in run_dict:
                run_dict["endTime"] = run_dict.pop("end_time")
            
            result = await self._db.evaluationRuns.insert_one(run_dict)
            logger.info(f"Created evaluation run: {run.id} for customer: {run.customer_id}")
            
            return run
            
        except DuplicateKeyError:
            raise ValueError(f"Evaluation run with ID {run.id} already exists")
        except PyMongoError as e:
            logger.error(f"Failed to create evaluation run: {e}")
            raise RuntimeError(f"Database error creating evaluation run: {e}") from e

    async def get_evaluation_runs(self, customer_id: str) -> List[EvaluationRun]:
        """
        Get all evaluation runs for a customer (tenant-scoped).
        
        Args:
            customer_id: Customer ID for tenant isolation
            
        Returns:
            List of evaluation runs for the customer
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            cursor = self._db.evaluationRuns.find({"customerId": customer_id})
            runs = []
            
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                doc["customer_id"] = doc.pop("customerId")
                doc["dataset_id"] = doc.pop("datasetId")
                doc["application_profile_id"] = doc.pop("applicationProfileId")
                doc["start_time"] = doc.pop("startTime")
                if "endTime" in doc:
                    doc["end_time"] = doc.pop("endTime")
                runs.append(EvaluationRun(**doc))
            
            return runs
            
        except PyMongoError as e:
            logger.error(f"Failed to get evaluation runs for customer {customer_id}: {e}")
            raise RuntimeError(f"Database error retrieving evaluation runs: {e}") from e

    async def get_evaluation_run_by_id(self, id: str, customer_id: str) -> Optional[EvaluationRun]:
        """
        Get evaluation run by ID with tenant check.
        
        Args:
            id: Evaluation run ID
            customer_id: Customer ID for tenant isolation
            
        Returns:
            EvaluationRun if found and belongs to customer, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            doc = await self._db.evaluationRuns.find_one({"_id": id, "customerId": customer_id})
            
            if doc:
                doc["id"] = str(doc.pop("_id"))
                doc["customer_id"] = doc.pop("customerId")
                doc["dataset_id"] = doc.pop("datasetId")
                doc["application_profile_id"] = doc.pop("applicationProfileId")
                doc["start_time"] = doc.pop("startTime")
                if "endTime" in doc:
                    doc["end_time"] = doc.pop("endTime")
                return EvaluationRun(**doc)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Failed to get evaluation run {id}: {e}")
            raise RuntimeError(f"Database error retrieving evaluation run: {e}") from e

    async def update_evaluation_run(self, id: str, customer_id: str, updates: Dict[str, Any]) -> EvaluationRun:
        """
        Update evaluation run with tenant check.
        
        Args:
            id: Evaluation run ID
            customer_id: Customer ID for tenant isolation
            updates: Dictionary of fields to update
            
        Returns:
            Updated evaluation run
            
        Raises:
            ValueError: If run not found or doesn't belong to customer
            RuntimeError: If database operation fails
        """
        try:
            # Convert snake_case to camelCase for MongoDB
            if "end_time" in updates:
                updates["endTime"] = updates.pop("end_time")
            
            result = await self._db.evaluationRuns.find_one_and_update(
                {"_id": id, "customerId": customer_id},
                {"$set": updates},
                return_document=True
            )
            
            if not result:
                raise ValueError(f"Evaluation run with ID {id} not found for customer {customer_id}")
            
            result["id"] = str(result.pop("_id"))
            result["customer_id"] = result.pop("customerId")
            result["dataset_id"] = result.pop("datasetId")
            result["application_profile_id"] = result.pop("applicationProfileId")
            result["start_time"] = result.pop("startTime")
            if "endTime" in result:
                result["end_time"] = result.pop("endTime")
            logger.info(f"Updated evaluation run: {id}")
            
            return EvaluationRun(**result)
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to update evaluation run {id}: {e}")
            raise RuntimeError(f"Database error updating evaluation run: {e}") from e

    # ==================== Response Operations ====================

    async def add_response(self, run_id: str, response: Response) -> None:
        """
        Add response to evaluation run.
        
        Args:
            run_id: Evaluation run ID
            response: Response object to add
            
        Raises:
            ValueError: If run not found
            RuntimeError: If database operation fails
        """
        try:
            response_dict = response.model_dump()
            
            # Convert snake_case to camelCase for MongoDB
            if "test_case_id" in response_dict:
                response_dict["testCaseId"] = response_dict.pop("test_case_id")
            if "individual_metrics" in response_dict:
                response_dict["individualMetrics"] = response_dict.pop("individual_metrics")
            
            result = await self._db.evaluationRuns.update_one(
                {"_id": run_id},
                {"$push": {"responses": response_dict}}
            )
            
            if result.matched_count == 0:
                raise ValueError(f"Evaluation run with ID {run_id} not found")
            
            logger.debug(f"Added response to evaluation run: {run_id}")
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to add response to run {run_id}: {e}")
            raise RuntimeError(f"Database error adding response: {e}") from e

    async def get_responses(self, run_id: str) -> List[Response]:
        """
        Get all responses for evaluation run.
        
        Args:
            run_id: Evaluation run ID
            
        Returns:
            List of responses
            
        Raises:
            ValueError: If run not found
            RuntimeError: If database operation fails
        """
        try:
            doc = await self._db.evaluationRuns.find_one({"_id": run_id}, {"responses": 1})
            
            if not doc:
                raise ValueError(f"Evaluation run with ID {run_id} not found")
            
            responses = []
            for response_dict in doc.get("responses", []):
                # Convert camelCase to snake_case for Pydantic
                if "testCaseId" in response_dict:
                    response_dict["test_case_id"] = response_dict.pop("testCaseId")
                if "individualMetrics" in response_dict:
                    response_dict["individual_metrics"] = response_dict.pop("individualMetrics")
                responses.append(Response(**response_dict))
            
            return responses
            
        except ValueError:
            raise
        except PyMongoError as e:
            logger.error(f"Failed to get responses for run {run_id}: {e}")
            raise RuntimeError(f"Database error retrieving responses: {e}") from e
