"""Unit tests for EvaluationEngine.

Tests the evaluation engine implementation including run execution,
customer validation, response capture, error handling, and partial
failure resilience.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.plugin import ApplicationResponse
from app.engine.evaluation_engine import EvaluationEngine
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.response import Response
from app.models.test_case import TestCase


class TestEvaluationEngineInitialization:
    """Test evaluation engine initialization."""
    
    def test_engine_initialization(self):
        """Test engine initializes with repository."""
        mock_repository = MagicMock()
        engine = EvaluationEngine(mock_repository)
        
        assert engine.repository == mock_repository


class TestEvaluationEngineExecuteRun:
    """Test evaluation run execution."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return AsyncMock()
    
    @pytest.fixture
    def engine(self, mock_repository):
        """Create evaluation engine instance."""
        return EvaluationEngine(mock_repository)
    
    @pytest.fixture
    def customer_id(self):
        """Create test customer ID."""
        return "cust_test123"
    
    @pytest.fixture
    def dataset(self, customer_id):
        """Create test dataset with test cases."""
        return Dataset(
            id="dataset_test123",
            customer_id=customer_id,
            name="Test Dataset",
            description="Test dataset for evaluation",
            test_cases=[
                TestCase(
                    id="tc_001",
                    input="What is 2+2?",
                    expected_output="4"
                ),
                TestCase(
                    id="tc_002",
                    input="What is the capital of France?",
                    expected_output="Paris"
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def application_profile(self, customer_id):
        """Create test application profile."""
        return ApplicationProfile(
            id="profile_test123",
            customer_id=customer_id,
            name="Test Application",
            type="chatbot",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com/v1/chat",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_execute_run_success(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset,
        application_profile
    ):
        """Test successful evaluation run execution."""
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = dataset
        mock_repository.get_application_profile_by_id.return_value = application_profile
        
        # Mock create_evaluation_run to return a run object
        created_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=dataset.id,
            application_profile_id=application_profile.id,
            status="running",
            start_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.create_evaluation_run.return_value = created_run
        
        # Mock add_response
        mock_repository.add_response.return_value = None
        
        # Mock update_evaluation_run to return completed run
        completed_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=dataset.id,
            application_profile_id=application_profile.id,
            status="completed",
            start_time=created_run.start_time,
            end_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.update_evaluation_run.return_value = completed_run
        
        # Mock plugin
        with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
            mock_plugin = AsyncMock()
            MockPlugin.return_value = mock_plugin
            
            # Mock plugin responses
            mock_plugin.send_input.side_effect = [
                ApplicationResponse(output="4", latency=100.0),
                ApplicationResponse(output="Paris", latency=150.0)
            ]
            
            # Execute run
            result = await engine.execute_run(
                customer_id,
                dataset.id,
                application_profile.id
            )
            
            # Verify repository calls
            mock_repository.get_dataset_by_id.assert_called_once_with(
                dataset.id,
                customer_id
            )
            mock_repository.get_application_profile_by_id.assert_called_once_with(
                application_profile.id
            )
            mock_repository.create_evaluation_run.assert_called_once()
            
            # Verify plugin was connected and disconnected
            mock_plugin.connect.assert_called_once()
            mock_plugin.disconnect.assert_called_once()
            
            # Verify responses were added
            assert mock_repository.add_response.call_count == 2
            
            # Verify run was completed
            mock_repository.update_evaluation_run.assert_called_once()
            assert result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_execute_run_dataset_not_found(
        self,
        engine,
        mock_repository,
        customer_id,
        application_profile
    ):
        """Test execution fails when dataset not found."""
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = None
        
        # Execute run and expect ValueError
        with pytest.raises(ValueError, match="Dataset .* not found"):
            await engine.execute_run(
                customer_id,
                "nonexistent_dataset",
                application_profile.id
            )
    
    @pytest.mark.asyncio
    async def test_execute_run_profile_not_found(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset
    ):
        """Test execution fails when application profile not found."""
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = dataset
        mock_repository.get_application_profile_by_id.return_value = None
        
        # Execute run and expect ValueError
        with pytest.raises(ValueError, match="Application profile .* not found"):
            await engine.execute_run(
                customer_id,
                dataset.id,
                "nonexistent_profile"
            )
    
    @pytest.mark.asyncio
    async def test_execute_run_customer_id_mismatch_dataset(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset,
        application_profile
    ):
        """Test execution fails when dataset doesn't belong to customer."""
        # Create dataset with different customer_id
        wrong_dataset = Dataset(
            id=dataset.id,
            customer_id="different_customer",
            name=dataset.name,
            description=dataset.description,
            test_cases=dataset.test_cases,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at
        )
        
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = wrong_dataset
        
        # Execute run and expect ValueError
        with pytest.raises(ValueError, match="does not belong to customer"):
            await engine.execute_run(
                customer_id,
                dataset.id,
                application_profile.id
            )
    
    @pytest.mark.asyncio
    async def test_execute_run_customer_id_mismatch_profile(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset,
        application_profile
    ):
        """Test execution fails when profile doesn't belong to customer."""
        # Create profile with different customer_id
        wrong_profile = ApplicationProfile(
            id=application_profile.id,
            customer_id="different_customer",
            name=application_profile.name,
            type=application_profile.type,
            connection_config=application_profile.connection_config,
            created_at=application_profile.created_at,
            updated_at=application_profile.updated_at
        )
        
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = dataset
        mock_repository.get_application_profile_by_id.return_value = wrong_profile
        
        # Execute run and expect ValueError
        with pytest.raises(ValueError, match="does not belong to customer"):
            await engine.execute_run(
                customer_id,
                dataset.id,
                application_profile.id
            )
    
    @pytest.mark.asyncio
    async def test_execute_run_partial_failure(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset,
        application_profile
    ):
        """Test execution continues when some test cases fail."""
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = dataset
        mock_repository.get_application_profile_by_id.return_value = application_profile
        
        # Mock create_evaluation_run
        created_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=dataset.id,
            application_profile_id=application_profile.id,
            status="running",
            start_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.create_evaluation_run.return_value = created_run
        
        # Mock add_response
        mock_repository.add_response.return_value = None
        
        # Mock update_evaluation_run
        completed_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=dataset.id,
            application_profile_id=application_profile.id,
            status="completed",
            start_time=created_run.start_time,
            end_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.update_evaluation_run.return_value = completed_run
        
        # Mock plugin with one success and one failure
        with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
            mock_plugin = AsyncMock()
            MockPlugin.return_value = mock_plugin
            
            # First test case succeeds, second fails
            mock_plugin.send_input.side_effect = [
                ApplicationResponse(output="4", latency=100.0),
                ApplicationResponse(
                    output="",
                    latency=50.0,
                    error="Connection timeout"
                )
            ]
            
            # Execute run
            result = await engine.execute_run(
                customer_id,
                dataset.id,
                application_profile.id
            )
            
            # Verify both responses were recorded
            assert mock_repository.add_response.call_count == 2
            
            # Verify run was completed (not failed)
            assert result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_execute_run_connection_failure(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset,
        application_profile
    ):
        """Test execution fails gracefully when connection fails."""
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = dataset
        mock_repository.get_application_profile_by_id.return_value = application_profile
        
        # Mock create_evaluation_run
        created_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=dataset.id,
            application_profile_id=application_profile.id,
            status="running",
            start_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.create_evaluation_run.return_value = created_run
        
        # Mock plugin connection failure
        with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
            mock_plugin = AsyncMock()
            MockPlugin.return_value = mock_plugin
            
            # Connection fails
            mock_plugin.connect.side_effect = ConnectionError("Cannot reach endpoint")
            
            # Execute run and expect ConnectionError
            with pytest.raises(ConnectionError, match="Cannot reach endpoint"):
                await engine.execute_run(
                    customer_id,
                    dataset.id,
                    application_profile.id
                )
    
    @pytest.mark.asyncio
    async def test_execute_run_single_test_case(
        self,
        engine,
        mock_repository,
        customer_id,
        dataset,
        application_profile
    ):
        """Test execution with dataset containing single test case."""
        # Create dataset with single test case
        single_dataset = Dataset(
            id="dataset_single",
            customer_id=customer_id,
            name="Single Test Case Dataset",
            description="Dataset with only one test case",
            test_cases=[
                TestCase(
                    id="tc_001",
                    input="What is 2+2?",
                    expected_output="4"
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = single_dataset
        mock_repository.get_application_profile_by_id.return_value = application_profile
        
        # Mock create_evaluation_run
        created_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=single_dataset.id,
            application_profile_id=application_profile.id,
            status="running",
            start_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.create_evaluation_run.return_value = created_run
        
        # Mock add_response
        mock_repository.add_response.return_value = None
        
        # Mock update_evaluation_run
        completed_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=single_dataset.id,
            application_profile_id=application_profile.id,
            status="completed",
            start_time=created_run.start_time,
            end_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.update_evaluation_run.return_value = completed_run
        
        # Mock plugin
        with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
            mock_plugin = AsyncMock()
            MockPlugin.return_value = mock_plugin
            
            # Mock single response
            mock_plugin.send_input.return_value = ApplicationResponse(
                output="4",
                latency=100.0
            )
            
            # Execute run
            result = await engine.execute_run(
                customer_id,
                single_dataset.id,
                application_profile.id
            )
            
            # Verify single response was added
            assert mock_repository.add_response.call_count == 1
            
            # Verify plugin was called once
            assert mock_plugin.send_input.call_count == 1
            
            # Verify run was completed
            assert result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_execute_run_empty_dataset(
        self,
        engine,
        mock_repository,
        customer_id,
        application_profile
    ):
        """Test execution with empty dataset (no test cases)."""
        # Create empty dataset
        empty_dataset = Dataset(
            id="dataset_empty",
            customer_id=customer_id,
            name="Empty Dataset",
            description="Dataset with no test cases",
            test_cases=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Setup mocks
        mock_repository.get_dataset_by_id.return_value = empty_dataset
        mock_repository.get_application_profile_by_id.return_value = application_profile
        
        # Mock create_evaluation_run
        created_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=empty_dataset.id,
            application_profile_id=application_profile.id,
            status="running",
            start_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.create_evaluation_run.return_value = created_run
        
        # Mock update_evaluation_run
        completed_run = EvaluationRun(
            id="run_test123",
            customer_id=customer_id,
            dataset_id=empty_dataset.id,
            application_profile_id=application_profile.id,
            status="completed",
            start_time=created_run.start_time,
            end_time=datetime.utcnow(),
            responses=[]
        )
        mock_repository.update_evaluation_run.return_value = completed_run
        
        # Mock plugin
        with patch('app.engine.evaluation_engine.HTTPPlugin') as MockPlugin:
            mock_plugin = AsyncMock()
            MockPlugin.return_value = mock_plugin
            
            # Execute run
            result = await engine.execute_run(
                customer_id,
                empty_dataset.id,
                application_profile.id
            )
            
            # Verify no responses were added
            mock_repository.add_response.assert_not_called()
            
            # Verify run was completed
            assert result.status == "completed"
            assert len(result.responses) == 0


class TestEvaluationEngineGetRunStatus:
    """Test getting evaluation run status."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return AsyncMock()
    
    @pytest.fixture
    def engine(self, mock_repository):
        """Create evaluation engine instance."""
        return EvaluationEngine(mock_repository)
    
    @pytest.mark.asyncio
    async def test_get_run_status_success(self, engine, mock_repository):
        """Test getting run status successfully."""
        customer_id = "cust_test123"
        run_id = "run_test123"
        
        # Create mock run
        mock_run = EvaluationRun(
            id=run_id,
            customer_id=customer_id,
            dataset_id="dataset_test123",
            application_profile_id="profile_test123",
            status="completed",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            responses=[
                Response(
                    test_case_id="tc_001",
                    input="test",
                    output="result",
                    latency=100.0,
                    timestamp=datetime.utcnow()
                ),
                Response(
                    test_case_id="tc_002",
                    input="test2",
                    output="",
                    latency=50.0,
                    timestamp=datetime.utcnow(),
                    error="Failed"
                )
            ]
        )
        
        mock_repository.get_evaluation_run_by_id.return_value = mock_run
        
        # Get status
        status = await engine.get_run_status(run_id, customer_id)
        
        # Verify status
        assert status["id"] == run_id
        assert status["status"] == "completed"
        assert status["total_test_cases"] == 2
        assert status["failed_test_cases"] == 1
    
    @pytest.mark.asyncio
    async def test_get_run_status_not_found(self, engine, mock_repository):
        """Test getting status for non-existent run."""
        customer_id = "cust_test123"
        run_id = "nonexistent_run"
        
        mock_repository.get_evaluation_run_by_id.return_value = None
        
        # Get status and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await engine.get_run_status(run_id, customer_id)
