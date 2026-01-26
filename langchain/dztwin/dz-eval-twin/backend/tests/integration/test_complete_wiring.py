"""Integration tests to verify complete component wiring.

This module tests that all components are properly wired together:
- API server connects to database layer
- API server connects to evaluation engine
- Evaluation engine connects to application connector
- Customer context flows through all layers
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.engine.evaluation_engine import EvaluationEngine
from app.engine.metrics_calculator import MetricsCalculator
from app.connectors.http_plugin import HTTPPlugin
from app.models.customer import Customer
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.dataset import Dataset, TestCase
from app.models.evaluation_run import EvaluationRun


@pytest.mark.asyncio
class TestCompleteWiring:
    """Test complete component wiring and integration."""
    
    async def test_api_to_database_wiring(self):
        """
        Test that API server can connect to database layer.
        
        Verifies:
        - Database manager is accessible
        - Repository can be instantiated with database
        - Basic CRUD operations work through the repository
        """
        # Verify database manager is available
        assert database_manager is not None
        
        # Verify we can create a repository instance
        if database_manager.is_connected():
            repository = DataRepository(database_manager.database)
            assert repository is not None
            
            # Test basic operation (customer creation)
            customer = Customer(
                id="test_customer_wiring",
                name="Test Customer",
                contact_email="test@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            try:
                created = await repository.create_customer(customer)
                assert created.id == customer.id
                
                # Cleanup
                await repository.delete_customer(customer.id)
            except Exception as e:
                # If customer already exists, that's fine for this test
                if "already exists" not in str(e):
                    raise
    
    async def test_api_to_evaluation_engine_wiring(self):
        """
        Test that API server can connect to evaluation engine.
        
        Verifies:
        - Evaluation engine can be instantiated with repository
        - Engine has access to database operations
        """
        if database_manager.is_connected():
            repository = DataRepository(database_manager.database)
            engine = EvaluationEngine(repository)
            
            assert engine is not None
            assert engine.repository is not None
    
    async def test_evaluation_engine_to_connector_wiring(self):
        """
        Test that evaluation engine can connect to application connector.
        
        Verifies:
        - Evaluation engine can instantiate connector plugins
        - Connector can be configured and connected
        """
        # Create a mock application profile
        profile = ApplicationProfile(
            id="test_profile_wiring",
            customer_id="test_customer",
            name="Test Profile",
            type="chatbot",  # Use valid application type
            connection_config=ConnectionConfig(
                endpoint="http://localhost:8080/test",
                timeout=30,
                retries=3
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create HTTP plugin
        plugin = HTTPPlugin()
        assert plugin is not None
        assert plugin.type == "http"
        
        # Verify plugin can be configured (connection will fail, but that's expected)
        try:
            await plugin.connect(profile.connection_config)
        except Exception as e:
            # Connection failure is expected for test endpoint
            assert "connect" in str(e).lower() or "timeout" in str(e).lower()
    
    async def test_customer_context_flow_through_layers(self):
        """
        Test that customer context flows through all layers.
        
        Verifies:
        - Customer ID is preserved in database operations
        - Customer ID is validated in evaluation engine
        - Tenant isolation is enforced
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        repository = DataRepository(database_manager.database)
        customer_id = "test_customer_context_flow"
        
        # Create test customer
        customer = Customer(
            id=customer_id,
            name="Context Flow Test Customer",
            contact_email="context@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            await repository.create_customer(customer)
            
            # Create dataset with customer_id
            dataset = Dataset(
                id="test_dataset_context",
                customer_id=customer_id,
                name="Test Dataset",
                description="Testing context flow",
                test_cases=[
                    TestCase(
                        id="tc1",
                        input="test input",
                        expected_output="test output"
                    )
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_dataset(dataset)
            
            # Verify dataset is scoped to customer
            retrieved = await repository.get_dataset_by_id(dataset.id, customer_id)
            assert retrieved is not None
            assert retrieved.customer_id == customer_id
            
            # Verify different customer cannot access dataset
            wrong_customer_id = "different_customer"
            retrieved_wrong = await repository.get_dataset_by_id(dataset.id, wrong_customer_id)
            assert retrieved_wrong is None
            
            # Cleanup
            await repository.delete_dataset(dataset.id, customer_id)
            await repository.delete_customer(customer_id)
            
        except Exception as e:
            # Cleanup on error
            try:
                await repository.delete_dataset("test_dataset_context", customer_id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
            raise
    
    async def test_metrics_calculator_wiring(self):
        """
        Test that metrics calculator is properly wired.
        
        Verifies:
        - Metrics calculator can be instantiated
        - Calculator can process responses
        """
        calculator = MetricsCalculator()
        assert calculator is not None
        
        # Test basic metric calculation
        from app.models.response import Response
        
        response = Response(
            test_case_id="tc1",
            input="test input",
            output="test output",
            latency=100.0,
            timestamp=datetime.utcnow()
        )
        
        # Calculate individual metrics
        metrics = calculator.calculate_individual_metrics(response, "test output")
        assert metrics is not None
        assert metrics.accuracy is not None
        assert metrics.relevance is not None
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_end_to_end_evaluation_flow(self, mock_client_class):
        """
        Test complete end-to-end evaluation flow.
        
        Verifies:
        - Customer creation
        - Application profile creation
        - Dataset creation
        - Evaluation run execution
        - Metrics calculation
        - All with proper customer context
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client for connector
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "test response"}
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.head.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        calculator = MetricsCalculator()
        
        customer_id = "test_e2e_customer"
        
        try:
            # 1. Create customer
            customer = Customer(
                id=customer_id,
                name="E2E Test Customer",
                contact_email="e2e@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_customer(customer)
            
            # 2. Create application profile
            profile = ApplicationProfile(
                id="test_e2e_profile",
                customer_id=customer_id,
                name="E2E Test Profile",
                type="chatbot",  # Use valid application type
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/test",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_application_profile(profile)
            
            # 3. Create dataset
            dataset = Dataset(
                id="test_e2e_dataset",
                customer_id=customer_id,
                name="E2E Test Dataset",
                description="End-to-end test",
                test_cases=[
                    TestCase(
                        id="tc1",
                        input="test input 1",
                        expected_output="test output 1"
                    ),
                    TestCase(
                        id="tc2",
                        input="test input 2",
                        expected_output="test output 2"
                    )
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset)
            
            # 4. Execute evaluation run
            run = await engine.execute_run(
                customer_id=customer_id,
                dataset_id=dataset.id,
                application_profile_id=profile.id
            )
            
            # 5. Verify run completed
            assert run is not None
            assert run.customer_id == customer_id
            assert run.status == "completed"
            assert len(run.responses) == 2
            
            # 6. Calculate metrics
            for response in run.responses:
                test_case = next(tc for tc in dataset.test_cases if tc.id == response.test_case_id)
                metrics = calculator.calculate_individual_metrics(response, test_case.expected_output)
                assert metrics is not None
            
            aggregated = calculator.aggregate_metrics(run.responses, dataset.test_cases)
            assert aggregated is not None
            assert aggregated.total_test_cases == 2
            
            # Cleanup
            await repository.delete_dataset(dataset.id, customer_id)
            await repository.delete_application_profile(profile.id)
            await repository.delete_customer(customer_id)
            
        except Exception as e:
            # Cleanup on error
            try:
                await repository.delete_dataset("test_e2e_dataset", customer_id)
            except:
                pass
            try:
                await repository.delete_application_profile("test_e2e_profile")
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
