"""Evaluation engine for executing test runs.

This module implements the core evaluation execution logic that runs
datasets against application profiles, captures responses, and handles
errors gracefully.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from app.connectors.http_plugin import HTTPPlugin
from app.connectors.plugin import ApplicationPlugin, ApplicationResponse
from app.database.repository import DataRepository
from app.models.application_profile import ApplicationProfile
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun, EvaluationStatus
from app.models.response import Response

logger = logging.getLogger(__name__)


class EvaluationEngine:
    """
    Engine for executing evaluation runs.
    
    The evaluation engine orchestrates the execution of test datasets
    against application profiles. It:
    - Validates customer_id matches for dataset and application profile
    - Iterates through test cases and sends inputs to the application
    - Captures responses with timestamps and latency measurements
    - Handles partial failures and error recording
    - Persists results to the database
    
    Attributes:
        repository: Data repository for database operations
    """
    
    def __init__(self, repository: DataRepository):
        """
        Initialize the evaluation engine.
        
        Args:
            repository: Data repository for database operations
        """
        self.repository = repository
    
    async def execute_run(
        self,
        customer_id: str,
        dataset_id: str,
        application_profile_id: str
    ) -> EvaluationRun:
        """
        Execute an evaluation run.
        
        This method performs the following steps:
        1. Verify customer_id matches for dataset and application profile
        2. Load dataset and application profile from database
        3. Create evaluation run record with customer_id
        4. Connect to the application via the appropriate plugin
        5. For each test case:
           a. Send input to application via connector
           b. Capture response and latency
           c. Store response in database
        6. Update run status to completed
        7. Return evaluation run
        
        The method handles partial failures gracefully - if individual
        test cases fail, it records the error and continues with remaining
        test cases.
        
        Args:
            customer_id: Customer ID for tenant isolation
            dataset_id: ID of the dataset to evaluate
            application_profile_id: ID of the application profile to test
        
        Returns:
            EvaluationRun with all responses and status
        
        Raises:
            ValueError: If customer_id doesn't match dataset or profile,
                       or if dataset/profile not found
            RuntimeError: If database operations fail
        """
        logger.info(
            f"Starting evaluation run for customer {customer_id}, "
            f"dataset {dataset_id}, profile {application_profile_id}"
        )
        
        # Step 1 & 2: Load and validate dataset
        dataset = await self._load_and_validate_dataset(customer_id, dataset_id)
        
        # Step 1 & 2: Load and validate application profile
        profile = await self._load_and_validate_profile(customer_id, application_profile_id)
        
        # Step 3: Create evaluation run record
        run = await self._create_evaluation_run(
            customer_id,
            dataset_id,
            application_profile_id
        )
        
        # Step 4: Connect to application
        plugin = await self._connect_to_application(profile)
        
        try:
            # Step 5: Execute test cases
            await self._execute_test_cases(run, dataset, plugin)
            
            # Step 6: Update run status to completed
            run = await self._complete_evaluation_run(run)
            
        except Exception as e:
            # If something goes catastrophically wrong, mark run as failed
            logger.error(f"Evaluation run {run.id} failed: {e}")
            run = await self._fail_evaluation_run(run, str(e))
            raise
        
        finally:
            # Always disconnect from application
            try:
                await plugin.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect plugin: {e}")
        
        logger.info(
            f"Completed evaluation run {run.id} with "
            f"{len(run.responses)} responses"
        )
        
        return run
    
    async def _load_and_validate_dataset(
        self,
        customer_id: str,
        dataset_id: str
    ) -> Dataset:
        """
        Load dataset and validate it belongs to the customer.
        
        Args:
            customer_id: Customer ID for tenant isolation
            dataset_id: Dataset ID to load
        
        Returns:
            Dataset object
        
        Raises:
            ValueError: If dataset not found or doesn't belong to customer
        """
        dataset = await self.repository.get_dataset_by_id(dataset_id, customer_id)
        
        if not dataset:
            raise ValueError(
                f"Dataset {dataset_id} not found for customer {customer_id}"
            )
        
        if dataset.customer_id != customer_id:
            raise ValueError(
                f"Dataset {dataset_id} does not belong to customer {customer_id}"
            )
        
        logger.debug(
            f"Loaded dataset {dataset_id} with {len(dataset.test_cases)} test cases"
        )
        
        return dataset
    
    async def _load_and_validate_profile(
        self,
        customer_id: str,
        application_profile_id: str
    ) -> ApplicationProfile:
        """
        Load application profile and validate it belongs to the customer.
        
        Args:
            customer_id: Customer ID for tenant isolation
            application_profile_id: Application profile ID to load
        
        Returns:
            ApplicationProfile object
        
        Raises:
            ValueError: If profile not found or doesn't belong to customer
        """
        profile = await self.repository.get_application_profile_by_id(
            application_profile_id
        )
        
        if not profile:
            raise ValueError(
                f"Application profile {application_profile_id} not found"
            )
        
        if profile.customer_id != customer_id:
            raise ValueError(
                f"Application profile {application_profile_id} does not belong "
                f"to customer {customer_id}"
            )
        
        logger.debug(f"Loaded application profile {application_profile_id}")
        
        return profile
    
    async def _create_evaluation_run(
        self,
        customer_id: str,
        dataset_id: str,
        application_profile_id: str
    ) -> EvaluationRun:
        """
        Create a new evaluation run record in the database.
        
        Args:
            customer_id: Customer ID for tenant isolation
            dataset_id: Dataset ID
            application_profile_id: Application profile ID
        
        Returns:
            Created EvaluationRun object
        
        Raises:
            RuntimeError: If database operation fails
        """
        run = EvaluationRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            customer_id=customer_id,
            dataset_id=dataset_id,
            application_profile_id=application_profile_id,
            status="running",
            start_time=datetime.utcnow(),
            responses=[]
        )
        
        created_run = await self.repository.create_evaluation_run(run)
        logger.info(f"Created evaluation run {created_run.id}")
        
        return created_run
    
    async def _connect_to_application(
        self,
        profile: ApplicationProfile
    ) -> ApplicationPlugin:
        """
        Create and connect to application plugin based on profile type.
        
        Currently supports HTTP plugin. Can be extended to support
        WebSocket and other plugin types.
        
        Args:
            profile: Application profile with connection configuration
        
        Returns:
            Connected ApplicationPlugin instance
        
        Raises:
            ValueError: If plugin type is not supported
            ConnectionError: If connection fails
        """
        # Determine plugin type from profile
        # For now, we'll use HTTP plugin as the default
        # In the future, this can be extended to support multiple plugin types
        plugin_type = profile.type.lower()
        
        if plugin_type in ["http", "chatbot", "rag", "agent", "workflow"]:
            plugin = HTTPPlugin()
        else:
            raise ValueError(f"Unsupported application type: {profile.type}")
        
        # Connect to application
        try:
            await plugin.connect(profile.connection_config)
            logger.debug(f"Connected to application via {plugin.type} plugin")
        except Exception as e:
            logger.error(f"Failed to connect to application: {e}")
            raise ConnectionError(
                f"Failed to connect to application: {str(e)}"
            ) from e
        
        return plugin
    
    async def _execute_test_cases(
        self,
        run: EvaluationRun,
        dataset: Dataset,
        plugin: ApplicationPlugin
    ) -> None:
        """
        Execute all test cases in the dataset.
        
        Iterates through test cases, sends inputs to the application,
        captures responses with timestamps and latency, and handles
        errors gracefully. If a test case fails, the error is recorded
        and execution continues with remaining test cases.
        
        Args:
            run: Evaluation run to update with responses
            dataset: Dataset containing test cases
            plugin: Connected application plugin
        
        Raises:
            RuntimeError: If database operations fail
        """
        logger.info(f"Executing {len(dataset.test_cases)} test cases")
        
        for test_case in dataset.test_cases:
            try:
                # Send input to application and capture response
                app_response = await plugin.send_input(test_case.input)
                
                # Create response record
                response = Response(
                    test_case_id=test_case.id,
                    input=test_case.input,
                    output=app_response.output,
                    latency=app_response.latency,
                    timestamp=datetime.utcnow(),
                    error=app_response.error
                )
                
                # Add response to database
                await self.repository.add_response(run.id, response)
                
                # Update local run object
                run.responses.append(response)
                
                if app_response.error:
                    logger.warning(
                        f"Test case {test_case.id} failed: {app_response.error}"
                    )
                else:
                    logger.debug(
                        f"Test case {test_case.id} completed in "
                        f"{app_response.latency:.2f}ms"
                    )
            
            except Exception as e:
                # If something goes wrong capturing the response,
                # record an error response and continue
                logger.error(f"Error executing test case {test_case.id}: {e}")
                
                error_response = Response(
                    test_case_id=test_case.id,
                    input=test_case.input,
                    output="",
                    latency=0.0,
                    timestamp=datetime.utcnow(),
                    error=f"Execution error: {str(e)}"
                )
                
                try:
                    await self.repository.add_response(run.id, error_response)
                    run.responses.append(error_response)
                except Exception as db_error:
                    logger.error(
                        f"Failed to record error response for test case "
                        f"{test_case.id}: {db_error}"
                    )
                    # Continue with next test case even if we can't record the error
    
    async def _complete_evaluation_run(self, run: EvaluationRun) -> EvaluationRun:
        """
        Mark evaluation run as completed.
        
        Updates the run status to 'completed' and sets the end time.
        
        Args:
            run: Evaluation run to complete
        
        Returns:
            Updated EvaluationRun object
        
        Raises:
            RuntimeError: If database operation fails
        """
        updates = {
            "status": "completed",
            "end_time": datetime.utcnow()
        }
        
        updated_run = await self.repository.update_evaluation_run(
            run.id,
            run.customer_id,
            updates
        )
        
        logger.info(f"Marked evaluation run {run.id} as completed")
        
        return updated_run
    
    async def _fail_evaluation_run(
        self,
        run: EvaluationRun,
        error_message: str
    ) -> EvaluationRun:
        """
        Mark evaluation run as failed.
        
        Updates the run status to 'failed' and sets the end time.
        
        Args:
            run: Evaluation run to mark as failed
            error_message: Error message describing the failure
        
        Returns:
            Updated EvaluationRun object
        
        Raises:
            RuntimeError: If database operation fails
        """
        updates = {
            "status": "failed",
            "end_time": datetime.utcnow()
        }
        
        try:
            updated_run = await self.repository.update_evaluation_run(
                run.id,
                run.customer_id,
                updates
            )
            logger.error(f"Marked evaluation run {run.id} as failed: {error_message}")
            return updated_run
        except Exception as e:
            logger.error(f"Failed to update run status to failed: {e}")
            # Return the original run if we can't update it
            run.status = "failed"
            run.end_time = datetime.utcnow()
            return run
    
    async def get_run_status(self, run_id: str, customer_id: str) -> Dict[str, any]:
        """
        Get the current status of an evaluation run.
        
        Args:
            run_id: Evaluation run ID
            customer_id: Customer ID for tenant isolation
        
        Returns:
            Dictionary with run status information
        
        Raises:
            ValueError: If run not found or doesn't belong to customer
            RuntimeError: If database operation fails
        """
        run = await self.repository.get_evaluation_run_by_id(run_id, customer_id)
        
        if not run:
            raise ValueError(
                f"Evaluation run {run_id} not found for customer {customer_id}"
            )
        
        return {
            "id": run.id,
            "status": run.status,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "total_test_cases": len(run.responses),
            "failed_test_cases": sum(1 for r in run.responses if r.error)
        }
