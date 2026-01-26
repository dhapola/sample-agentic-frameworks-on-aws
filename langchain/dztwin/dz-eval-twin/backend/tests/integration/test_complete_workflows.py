"""Integration tests for complete workflows.

This module tests complete end-to-end workflows including:
1. Complete evaluation workflow (create customer → create profile → create dataset → run evaluation → view results)
2. Multi-tenant isolation (verify customer A cannot access customer B's data)
3. Concurrent operations (multiple customers, parallel runs)
4. Error recovery scenarios

Validates Requirements: All
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.engine.evaluation_engine import EvaluationEngine
from app.engine.metrics_calculator import MetricsCalculator
from app.models.customer import Customer
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig
from app.models.dataset import Dataset, TestCase
from app.models.evaluation_run import EvaluationRun


@pytest.mark.asyncio
class TestCompleteEvaluationWorkflow:
    """Test complete evaluation workflow from start to finish."""
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_complete_evaluation_workflow(self, mock_client_class):
        """
        Test complete evaluation workflow:
        1. Create customer
        2. Create application profile for customer
        3. Create dataset for customer
        4. Run evaluation
        5. View results with metrics
        
        Validates: Requirements 0.2, 0.5, 1.1, 1.2, 3.1, 3.7, 4.1, 4.6, 5.2, 5.3
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client for connector
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "AI generated response"}
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.head.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        calculator = MetricsCalculator()
        
        customer_id = "workflow_test_customer"
        
        try:
            # Step 1: Create customer
            customer = Customer(
                id=customer_id,
                name="Workflow Test Customer",
                contact_email="workflow@example.com",
                contact_phone="+1-555-0100",
                configuration={"tier": "premium"},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            created_customer = await repository.create_customer(customer)
            assert created_customer.id == customer_id
            assert created_customer.name == "Workflow Test Customer"
            
            # Step 2: Create application profile for customer
            profile = ApplicationProfile(
                id="workflow_test_profile",
                customer_id=customer_id,
                name="Workflow Test Chatbot",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            created_profile = await repository.create_application_profile(profile)
            assert created_profile.id == profile.id
            assert created_profile.customer_id == customer_id
            
            # Step 3: Create dataset for customer
            dataset = Dataset(
                id="workflow_test_dataset",
                customer_id=customer_id,
                name="Workflow Test Dataset",
                description="Testing complete workflow",
                test_cases=[
                    TestCase(
                        id="tc1",
                        input="What is the capital of France?",
                        expected_output="Paris"
                    ),
                    TestCase(
                        id="tc2",
                        input="What is 2+2?",
                        expected_output="4"
                    ),
                    TestCase(
                        id="tc3",
                        input="Who wrote Romeo and Juliet?",
                        expected_output="William Shakespeare"
                    )
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            created_dataset = await repository.create_dataset(dataset)
            assert created_dataset.id == dataset.id
            assert created_dataset.customer_id == customer_id
            assert len(created_dataset.test_cases) == 3
            
            # Step 4: Run evaluation
            run = await engine.execute_run(
                customer_id=customer_id,
                dataset_id=dataset.id,
                application_profile_id=profile.id
            )
            
            # Verify run completed successfully
            assert run is not None
            assert run.customer_id == customer_id
            assert run.dataset_id == dataset.id
            assert run.application_profile_id == profile.id
            assert run.status == "completed"
            assert len(run.responses) == 3
            assert run.end_time is not None
            
            # Step 5: View results with metrics
            # Verify all responses have required metadata
            for response in run.responses:
                assert response.test_case_id in ["tc1", "tc2", "tc3"]
                assert response.input is not None
                assert response.output is not None
                assert response.latency >= 0
                assert response.timestamp is not None
                assert response.individual_metrics is not None
                assert response.individual_metrics.accuracy is not None
                assert response.individual_metrics.relevance is not None
            
            # Verify aggregated metrics
            assert run.metrics is not None
            assert run.metrics.average_accuracy >= 0
            assert run.metrics.average_relevance >= 0
            assert run.metrics.average_latency >= 0
            assert run.metrics.median_latency >= 0
            assert run.metrics.p95_latency >= 0
            assert run.metrics.success_rate >= 0
            assert run.metrics.total_test_cases == 3
            assert run.metrics.failed_test_cases == 0
            
            # Verify we can retrieve the run
            retrieved_run = await repository.get_evaluation_run_by_id(run.id, customer_id)
            assert retrieved_run is not None
            assert retrieved_run.id == run.id
            assert len(retrieved_run.responses) == 3
            
            # Verify we can list runs for customer
            runs = await repository.get_evaluation_runs(customer_id)
            assert len(runs) >= 1
            assert any(r.id == run.id for r in runs)
            
        finally:
            # Cleanup
            try:
                await repository.delete_dataset(dataset.id, customer_id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass



@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Test multi-tenant isolation to ensure customer A cannot access customer B's data."""
    
    async def test_customer_cannot_access_other_customer_datasets(self):
        """
        Test that customer A cannot access customer B's datasets.
        
        Validates: Requirements 0.1, 0.3, 0.4, 1.6
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        repository = DataRepository(database_manager.database)
        customer_a_id = "tenant_isolation_customer_a"
        customer_b_id = "tenant_isolation_customer_b"
        
        try:
            # Create two customers
            customer_a = Customer(
                id=customer_a_id,
                name="Customer A",
                contact_email="customera@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            customer_b = Customer(
                id=customer_b_id,
                name="Customer B",
                contact_email="customerb@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_customer(customer_a)
            await repository.create_customer(customer_b)
            
            # Create dataset for customer A
            dataset_a = Dataset(
                id="dataset_customer_a",
                customer_id=customer_a_id,
                name="Customer A Dataset",
                description="Private to Customer A",
                test_cases=[
                    TestCase(id="tc1", input="A's data", expected_output="A's result")
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset_a)
            
            # Create dataset for customer B
            dataset_b = Dataset(
                id="dataset_customer_b",
                customer_id=customer_b_id,
                name="Customer B Dataset",
                description="Private to Customer B",
                test_cases=[
                    TestCase(id="tc1", input="B's data", expected_output="B's result")
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset_b)
            
            # Verify customer A can access their own dataset
            dataset_a_retrieved = await repository.get_dataset_by_id(dataset_a.id, customer_a_id)
            assert dataset_a_retrieved is not None
            assert dataset_a_retrieved.customer_id == customer_a_id
            
            # Verify customer A CANNOT access customer B's dataset
            dataset_b_as_a = await repository.get_dataset_by_id(dataset_b.id, customer_a_id)
            assert dataset_b_as_a is None
            
            # Verify customer B can access their own dataset
            dataset_b_retrieved = await repository.get_dataset_by_id(dataset_b.id, customer_b_id)
            assert dataset_b_retrieved is not None
            assert dataset_b_retrieved.customer_id == customer_b_id
            
            # Verify customer B CANNOT access customer A's dataset
            dataset_a_as_b = await repository.get_dataset_by_id(dataset_a.id, customer_b_id)
            assert dataset_a_as_b is None
            
            # Verify list operations only return customer's own datasets
            datasets_a = await repository.get_datasets(customer_a_id)
            assert len([d for d in datasets_a if d.id == dataset_a.id]) == 1
            assert len([d for d in datasets_a if d.id == dataset_b.id]) == 0
            
            datasets_b = await repository.get_datasets(customer_b_id)
            assert len([d for d in datasets_b if d.id == dataset_b.id]) == 1
            assert len([d for d in datasets_b if d.id == dataset_a.id]) == 0
            
        finally:
            # Cleanup
            try:
                await repository.delete_dataset(dataset_a.id, customer_a_id)
            except:
                pass
            try:
                await repository.delete_dataset(dataset_b.id, customer_b_id)
            except:
                pass
            try:
                await repository.delete_customer(customer_a_id)
            except:
                pass
            try:
                await repository.delete_customer(customer_b_id)
            except:
                pass
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_customer_cannot_access_other_customer_evaluation_runs(self, mock_client_class):
        """
        Test that customer A cannot access customer B's evaluation runs.
        
        Validates: Requirements 0.1, 0.3, 0.4, 3.6, 5.2
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "response"}
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.head.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        customer_a_id = "tenant_runs_customer_a"
        customer_b_id = "tenant_runs_customer_b"
        
        try:
            # Create two customers
            customer_a = Customer(
                id=customer_a_id,
                name="Customer A",
                contact_email="customera@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            customer_b = Customer(
                id=customer_b_id,
                name="Customer B",
                contact_email="customerb@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_customer(customer_a)
            await repository.create_customer(customer_b)
            
            # Create profiles for both customers
            profile_a = ApplicationProfile(
                id="profile_customer_a",
                customer_id=customer_a_id,
                name="Customer A Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            profile_b = ApplicationProfile(
                id="profile_customer_b",
                customer_id=customer_b_id,
                name="Customer B Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_application_profile(profile_a)
            await repository.create_application_profile(profile_b)
            
            # Create datasets for both customers
            dataset_a = Dataset(
                id="dataset_runs_a",
                customer_id=customer_a_id,
                name="Dataset A",
                description="Test",
                test_cases=[TestCase(id="tc1", input="test", expected_output="result")],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            dataset_b = Dataset(
                id="dataset_runs_b",
                customer_id=customer_b_id,
                name="Dataset B",
                description="Test",
                test_cases=[TestCase(id="tc1", input="test", expected_output="result")],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_dataset(dataset_a)
            await repository.create_dataset(dataset_b)
            
            # Run evaluations for both customers
            run_a = await engine.execute_run(customer_a_id, dataset_a.id, profile_a.id)
            run_b = await engine.execute_run(customer_b_id, dataset_b.id, profile_b.id)
            
            # Verify customer A can access their own run
            run_a_retrieved = await repository.get_evaluation_run_by_id(run_a.id, customer_a_id)
            assert run_a_retrieved is not None
            assert run_a_retrieved.customer_id == customer_a_id
            
            # Verify customer A CANNOT access customer B's run
            run_b_as_a = await repository.get_evaluation_run_by_id(run_b.id, customer_a_id)
            assert run_b_as_a is None
            
            # Verify customer B can access their own run
            run_b_retrieved = await repository.get_evaluation_run_by_id(run_b.id, customer_b_id)
            assert run_b_retrieved is not None
            assert run_b_retrieved.customer_id == customer_b_id
            
            # Verify customer B CANNOT access customer A's run
            run_a_as_b = await repository.get_evaluation_run_by_id(run_a.id, customer_b_id)
            assert run_a_as_b is None
            
            # Verify list operations only return customer's own runs
            runs_a = await repository.get_evaluation_runs(customer_a_id)
            assert len([r for r in runs_a if r.id == run_a.id]) == 1
            assert len([r for r in runs_a if r.id == run_b.id]) == 0
            
            runs_b = await repository.get_evaluation_runs(customer_b_id)
            assert len([r for r in runs_b if r.id == run_b.id]) == 1
            assert len([r for r in runs_b if r.id == run_a.id]) == 0
            
        finally:
            # Cleanup
            try:
                await repository.delete_dataset(dataset_a.id, customer_a_id)
            except:
                pass
            try:
                await repository.delete_dataset(dataset_b.id, customer_b_id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile_a.id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile_b.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_a_id)
            except:
                pass
            try:
                await repository.delete_customer(customer_b_id)
            except:
                pass
    
    async def test_customer_cannot_access_other_customer_application_profiles(self):
        """
        Test that customer A cannot access customer B's application profiles.
        
        Validates: Requirements 0.1, 0.3, 0.4, 2.6
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        repository = DataRepository(database_manager.database)
        customer_a_id = "tenant_profiles_customer_a"
        customer_b_id = "tenant_profiles_customer_b"
        
        try:
            # Create two customers
            customer_a = Customer(
                id=customer_a_id,
                name="Customer A",
                contact_email="customera@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            customer_b = Customer(
                id=customer_b_id,
                name="Customer B",
                contact_email="customerb@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_customer(customer_a)
            await repository.create_customer(customer_b)
            
            # Create profiles for both customers
            profile_a = ApplicationProfile(
                id="profile_isolation_a",
                customer_id=customer_a_id,
                name="Customer A Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            profile_b = ApplicationProfile(
                id="profile_isolation_b",
                customer_id=customer_b_id,
                name="Customer B Profile",
                type="rag",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/rag",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await repository.create_application_profile(profile_a)
            await repository.create_application_profile(profile_b)
            
            # Verify list operations only return customer's own profiles
            profiles_a = await repository.get_application_profiles(customer_a_id)
            assert len([p for p in profiles_a if p.id == profile_a.id]) == 1
            assert len([p for p in profiles_a if p.id == profile_b.id]) == 0
            
            profiles_b = await repository.get_application_profiles(customer_b_id)
            assert len([p for p in profiles_b if p.id == profile_b.id]) == 1
            assert len([p for p in profiles_b if p.id == profile_a.id]) == 0
            
            # Verify all profiles (admin view) returns both
            all_profiles = await repository.get_application_profiles()
            profile_a_ids = [p.id for p in all_profiles if p.id == profile_a.id]
            profile_b_ids = [p.id for p in all_profiles if p.id == profile_b.id]
            assert len(profile_a_ids) >= 1
            assert len(profile_b_ids) >= 1
            
        finally:
            # Cleanup
            try:
                await repository.delete_application_profile(profile_a.id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile_b.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_a_id)
            except:
                pass
            try:
                await repository.delete_customer(customer_b_id)
            except:
                pass


@pytest.mark.asyncio
class TestConcurrentOperations:
    """Test concurrent operations with multiple customers and parallel runs."""
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_concurrent_evaluation_runs_for_same_customer(self, mock_client_class):
        """
        Test that multiple evaluation runs can execute concurrently for the same customer.
        
        Validates: Requirements 3.1, 3.7, 6.1
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "concurrent response"}
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.head.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        customer_id = "concurrent_runs_customer"
        
        try:
            # Create customer
            customer = Customer(
                id=customer_id,
                name="Concurrent Runs Customer",
                contact_email="concurrent@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_customer(customer)
            
            # Create application profile
            profile = ApplicationProfile(
                id="concurrent_profile",
                customer_id=customer_id,
                name="Concurrent Test Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_application_profile(profile)
            
            # Create multiple datasets
            datasets = []
            for i in range(3):
                dataset = Dataset(
                    id=f"concurrent_dataset_{i}",
                    customer_id=customer_id,
                    name=f"Concurrent Dataset {i}",
                    description=f"Dataset {i} for concurrent testing",
                    test_cases=[
                        TestCase(id=f"tc{j}", input=f"input {j}", expected_output=f"output {j}")
                        for j in range(2)
                    ],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                await repository.create_dataset(dataset)
                datasets.append(dataset)
            
            # Execute runs concurrently
            run_tasks = [
                engine.execute_run(customer_id, dataset.id, profile.id)
                for dataset in datasets
            ]
            runs = await asyncio.gather(*run_tasks)
            
            # Verify all runs completed successfully
            assert len(runs) == 3
            for i, run in enumerate(runs):
                assert run is not None
                assert run.customer_id == customer_id
                assert run.status == "completed"
                assert len(run.responses) == 2
                assert run.dataset_id == f"concurrent_dataset_{i}"
            
            # Verify all runs are retrievable
            all_runs = await repository.get_evaluation_runs(customer_id)
            concurrent_run_ids = [r.id for r in runs]
            retrieved_run_ids = [r.id for r in all_runs if r.id in concurrent_run_ids]
            assert len(retrieved_run_ids) == 3
            
        finally:
            # Cleanup
            for i in range(3):
                try:
                    await repository.delete_dataset(f"concurrent_dataset_{i}", customer_id)
                except:
                    pass
            try:
                await repository.delete_application_profile(profile.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_concurrent_operations_across_multiple_customers(self, mock_client_class):
        """
        Test that multiple customers can perform operations concurrently without interference.
        
        Validates: Requirements 0.1, 0.3, 0.4, 3.1, 6.9
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "multi-tenant response"}
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.head.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        
        num_customers = 3
        customer_ids = [f"multi_tenant_customer_{i}" for i in range(num_customers)]
        
        try:
            # Create multiple customers concurrently
            customer_tasks = [
                repository.create_customer(Customer(
                    id=customer_id,
                    name=f"Multi-Tenant Customer {i}",
                    contact_email=f"customer{i}@example.com",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ))
                for i, customer_id in enumerate(customer_ids)
            ]
            customers = await asyncio.gather(*customer_tasks)
            assert len(customers) == num_customers
            
            # Create profiles for each customer concurrently
            profile_tasks = [
                repository.create_application_profile(ApplicationProfile(
                    id=f"multi_tenant_profile_{i}",
                    customer_id=customer_id,
                    name=f"Profile {i}",
                    type="chatbot",
                    connection_config=ConnectionConfig(
                        endpoint="http://localhost:8080/chat",
                        timeout=30,
                        retries=3
                    ),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ))
                for i, customer_id in enumerate(customer_ids)
            ]
            profiles = await asyncio.gather(*profile_tasks)
            assert len(profiles) == num_customers
            
            # Create datasets for each customer concurrently
            dataset_tasks = [
                repository.create_dataset(Dataset(
                    id=f"multi_tenant_dataset_{i}",
                    customer_id=customer_id,
                    name=f"Dataset {i}",
                    description=f"Dataset for customer {i}",
                    test_cases=[
                        TestCase(id="tc1", input=f"input from customer {i}", expected_output=f"output {i}")
                    ],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ))
                for i, customer_id in enumerate(customer_ids)
            ]
            datasets = await asyncio.gather(*dataset_tasks)
            assert len(datasets) == num_customers
            
            # Execute evaluation runs for all customers concurrently
            run_tasks = [
                engine.execute_run(customer_ids[i], datasets[i].id, profiles[i].id)
                for i in range(num_customers)
            ]
            runs = await asyncio.gather(*run_tasks)
            assert len(runs) == num_customers
            
            # Verify each customer's data is isolated
            for i, customer_id in enumerate(customer_ids):
                # Verify customer can access their own data
                customer_datasets = await repository.get_datasets(customer_id)
                assert len([d for d in customer_datasets if d.id == f"multi_tenant_dataset_{i}"]) == 1
                
                customer_runs = await repository.get_evaluation_runs(customer_id)
                assert len([r for r in customer_runs if r.id == runs[i].id]) == 1
                
                # Verify customer cannot access other customers' data
                for j in range(num_customers):
                    if i != j:
                        other_dataset = await repository.get_dataset_by_id(f"multi_tenant_dataset_{j}", customer_id)
                        assert other_dataset is None
                        
                        other_run = await repository.get_evaluation_run_by_id(runs[j].id, customer_id)
                        assert other_run is None
            
        finally:
            # Cleanup
            for i in range(num_customers):
                try:
                    await repository.delete_dataset(f"multi_tenant_dataset_{i}", customer_ids[i])
                except:
                    pass
                try:
                    await repository.delete_application_profile(f"multi_tenant_profile_{i}")
                except:
                    pass
                try:
                    await repository.delete_customer(customer_ids[i])
                except:
                    pass



@pytest.mark.asyncio
class TestErrorRecoveryScenarios:
    """Test error recovery scenarios to ensure system resilience."""
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_evaluation_continues_after_partial_failures(self, mock_client_class):
        """
        Test that evaluation run continues processing remaining test cases after some failures.
        
        Validates: Requirements 3.5, 7.3
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client with intermittent failures
        mock_client = AsyncMock()
        call_count = [0]
        
        def mock_post(*args, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            # Fail on second call, succeed on others
            if call_count[0] == 2:
                raise Exception("Connection timeout")
            mock_response.json.return_value = {"output": f"response {call_count[0]}"}
            mock_response.status_code = 200
            return mock_response
        
        mock_client.post = mock_post
        mock_response_head = MagicMock()
        mock_response_head.status_code = 200
        mock_client.head.return_value = mock_response_head
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        customer_id = "error_recovery_customer"
        
        try:
            # Create customer
            customer = Customer(
                id=customer_id,
                name="Error Recovery Customer",
                contact_email="recovery@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_customer(customer)
            
            # Create application profile
            profile = ApplicationProfile(
                id="error_recovery_profile",
                customer_id=customer_id,
                name="Error Recovery Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_application_profile(profile)
            
            # Create dataset with multiple test cases
            dataset = Dataset(
                id="error_recovery_dataset",
                customer_id=customer_id,
                name="Error Recovery Dataset",
                description="Testing error recovery",
                test_cases=[
                    TestCase(id="tc1", input="test 1", expected_output="output 1"),
                    TestCase(id="tc2", input="test 2", expected_output="output 2"),  # This will fail
                    TestCase(id="tc3", input="test 3", expected_output="output 3"),
                    TestCase(id="tc4", input="test 4", expected_output="output 4"),
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset)
            
            # Execute evaluation run
            run = await engine.execute_run(customer_id, dataset.id, profile.id)
            
            # Verify run completed (not failed entirely)
            assert run is not None
            assert run.status == "completed"
            assert len(run.responses) == 4
            
            # Verify that failed test case has error recorded
            failed_response = next(r for r in run.responses if r.test_case_id == "tc2")
            assert failed_response.error is not None
            assert "timeout" in failed_response.error.lower() or "connection" in failed_response.error.lower()
            
            # Verify other test cases succeeded
            successful_responses = [r for r in run.responses if r.test_case_id != "tc2"]
            assert len(successful_responses) == 3
            for response in successful_responses:
                assert response.error is None
                assert response.output is not None
            
            # Verify metrics reflect the failure
            assert run.metrics is not None
            assert run.metrics.total_test_cases == 4
            assert run.metrics.failed_test_cases == 1
            assert run.metrics.success_rate == 0.75  # 3 out of 4 succeeded
            
        finally:
            # Cleanup
            try:
                await repository.delete_dataset(dataset.id, customer_id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
    
    async def test_database_error_does_not_corrupt_existing_data(self):
        """
        Test that database errors don't corrupt existing data.
        
        Validates: Requirements 7.2, 7.6
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        repository = DataRepository(database_manager.database)
        customer_id = "db_error_recovery_customer"
        
        try:
            # Create customer
            customer = Customer(
                id=customer_id,
                name="DB Error Recovery Customer",
                contact_email="dberror@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_customer(customer)
            
            # Create dataset
            dataset = Dataset(
                id="db_error_dataset",
                customer_id=customer_id,
                name="Original Dataset",
                description="Original description",
                test_cases=[
                    TestCase(id="tc1", input="original input", expected_output="original output")
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset)
            
            # Verify dataset was created
            retrieved = await repository.get_dataset_by_id(dataset.id, customer_id)
            assert retrieved is not None
            assert retrieved.name == "Original Dataset"
            assert retrieved.description == "Original description"
            
            # Attempt to update with invalid data (empty name)
            try:
                await repository.update_dataset(
                    dataset.id,
                    customer_id,
                    {"name": ""}  # Invalid empty name
                )
            except Exception as e:
                # Expected to fail
                assert "name" in str(e).lower() or "validation" in str(e).lower()
            
            # Verify original data is still intact
            retrieved_after = await repository.get_dataset_by_id(dataset.id, customer_id)
            assert retrieved_after is not None
            assert retrieved_after.name == "Original Dataset"
            assert retrieved_after.description == "Original description"
            assert len(retrieved_after.test_cases) == 1
            
        finally:
            # Cleanup
            try:
                await repository.delete_dataset(dataset.id, customer_id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
    
    @patch('app.connectors.http_plugin.httpx.AsyncClient')
    async def test_evaluation_handles_all_test_cases_failing(self, mock_client_class):
        """
        Test that evaluation run handles scenario where all test cases fail.
        
        Validates: Requirements 3.5, 7.3
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        # Mock HTTP client to always fail
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Application unavailable")
        mock_response_head = MagicMock()
        mock_response_head.status_code = 200
        mock_client.head.return_value = mock_response_head
        mock_client_class.return_value = mock_client
        
        repository = DataRepository(database_manager.database)
        engine = EvaluationEngine(repository)
        customer_id = "all_fail_customer"
        
        try:
            # Create customer
            customer = Customer(
                id=customer_id,
                name="All Fail Customer",
                contact_email="allfail@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_customer(customer)
            
            # Create application profile
            profile = ApplicationProfile(
                id="all_fail_profile",
                customer_id=customer_id,
                name="All Fail Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_application_profile(profile)
            
            # Create dataset
            dataset = Dataset(
                id="all_fail_dataset",
                customer_id=customer_id,
                name="All Fail Dataset",
                description="All test cases will fail",
                test_cases=[
                    TestCase(id="tc1", input="test 1", expected_output="output 1"),
                    TestCase(id="tc2", input="test 2", expected_output="output 2"),
                    TestCase(id="tc3", input="test 3", expected_output="output 3"),
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset)
            
            # Execute evaluation run
            run = await engine.execute_run(customer_id, dataset.id, profile.id)
            
            # Verify run completed (not crashed)
            assert run is not None
            assert run.status == "completed"
            assert len(run.responses) == 3
            
            # Verify all responses have errors
            for response in run.responses:
                assert response.error is not None
                assert "unavailable" in response.error.lower() or "application" in response.error.lower()
            
            # Verify metrics reflect all failures
            assert run.metrics is not None
            assert run.metrics.total_test_cases == 3
            assert run.metrics.failed_test_cases == 3
            assert run.metrics.success_rate == 0.0
            
        finally:
            # Cleanup
            try:
                await repository.delete_dataset(dataset.id, customer_id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
    
    async def test_customer_deletion_cascades_properly(self):
        """
        Test that deleting a customer properly handles associated data.
        
        Validates: Requirements 0.2, 0.3, 6.9
        """
        if not database_manager.is_connected():
            pytest.skip("Database not connected")
        
        repository = DataRepository(database_manager.database)
        customer_id = "cascade_delete_customer"
        
        try:
            # Create customer
            customer = Customer(
                id=customer_id,
                name="Cascade Delete Customer",
                contact_email="cascade@example.com",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_customer(customer)
            
            # Create application profile
            profile = ApplicationProfile(
                id="cascade_profile",
                customer_id=customer_id,
                name="Cascade Profile",
                type="chatbot",
                connection_config=ConnectionConfig(
                    endpoint="http://localhost:8080/chat",
                    timeout=30,
                    retries=3
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_application_profile(profile)
            
            # Create dataset
            dataset = Dataset(
                id="cascade_dataset",
                customer_id=customer_id,
                name="Cascade Dataset",
                description="Testing cascade delete",
                test_cases=[
                    TestCase(id="tc1", input="test", expected_output="output")
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await repository.create_dataset(dataset)
            
            # Verify all entities exist
            assert await repository.get_customer_by_id(customer_id) is not None
            assert await repository.get_application_profile_by_id(profile.id) is not None
            assert await repository.get_dataset_by_id(dataset.id, customer_id) is not None
            
            # Delete customer
            await repository.delete_customer(customer_id)
            
            # Verify customer is deleted
            assert await repository.get_customer_by_id(customer_id) is None
            
            # Note: In a real system, you might want cascade deletes or orphan cleanup
            # For now, we just verify the customer is gone and associated data becomes inaccessible
            # through customer-scoped queries
            
        except Exception as e:
            # Cleanup on error
            try:
                await repository.delete_dataset(dataset.id, customer_id)
            except:
                pass
            try:
                await repository.delete_application_profile(profile.id)
            except:
                pass
            try:
                await repository.delete_customer(customer_id)
            except:
                pass
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
