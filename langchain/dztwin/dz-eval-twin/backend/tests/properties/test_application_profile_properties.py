"""Property-based tests for application profile operations.

Feature: gen-ai-eval-platform
Property 5: Application configuration persistence round-trip
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, Optional

from app.database.repository import DataRepository
from app.models.application_profile import ApplicationProfile
from app.models.connection_config import ConnectionConfig


# ==================== Hypothesis Strategies ====================

@st.composite
def connection_config_strategy(draw):
    """Generate valid ConnectionConfig objects."""
    # Generate valid URL
    protocol = "https"
    domain = draw(st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'))
    path = draw(st.text(min_size=0, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz/'))
    endpoint = f"{protocol}://api.{domain}.com/{path}".rstrip('/')
    
    # Optional authentication
    auth = None
    if draw(st.booleans()):
        auth_type = draw(st.sampled_from(["bearer", "api_key", "basic"]))
        auth = {
            "type": auth_type,
            "token": draw(st.text(min_size=10, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'))
        }
    
    # Timeout and retries
    timeout = draw(st.integers(min_value=1, max_value=300))
    retries = draw(st.integers(min_value=0, max_value=10))
    
    # Optional custom headers
    custom_headers = None
    if draw(st.booleans()):
        num_headers = draw(st.integers(min_value=1, max_value=3))
        custom_headers = {}
        for i in range(num_headers):
            header_name = f"X-Custom-{draw(st.text(min_size=3, max_size=10, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ'))}"
            header_value = draw(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'))
            custom_headers[header_name] = header_value
    
    return ConnectionConfig(
        endpoint=endpoint,
        authentication=auth,
        timeout=timeout,
        retries=retries,
        custom_headers=custom_headers
    )


@st.composite
def application_profile_strategy(draw):
    """Generate valid ApplicationProfile objects."""
    profile_id = f"app_{draw(st.integers(min_value=1000, max_value=9999))}"
    customer_id = f"cust_{draw(st.integers(min_value=1000, max_value=9999))}"
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '
    )))
    app_type = draw(st.sampled_from(["chatbot", "rag", "agent", "workflow", "custom"]))
    connection_config = draw(connection_config_strategy())
    
    return ApplicationProfile(
        id=profile_id,
        customer_id=customer_id,
        name=name.strip() or "Test Profile",  # Ensure non-empty
        type=app_type,
        connection_config=connection_config,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(profile=application_profile_strategy())
async def test_application_profile_persistence_round_trip(profile: ApplicationProfile):
    """
    Property 5: Application configuration persistence round-trip.
    
    **Validates: Requirements 2.2, 2.7, 6.4**
    
    For any application configuration, registering the application then
    retrieving it should return an equivalent configuration.
    """
    # Create mock database
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.applicationProfiles = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Storage for the created profile document
    stored_doc = {}
    
    # Mock insert_one to store the profile
    async def mock_insert_one(doc):
        stored_doc.update(doc)
        result = MagicMock()
        result.inserted_id = doc["_id"]
        return result
    
    mock_database.applicationProfiles.insert_one = mock_insert_one
    
    # Mock find_one to retrieve the stored profile
    # Note: The repository stores in camelCase, so we return it as-is
    async def mock_find_one(query):
        if query.get("_id") == profile.id:
            # Return the stored document which is already in camelCase format
            return stored_doc.copy()
        return None
    
    mock_database.applicationProfiles.find_one = mock_find_one
    
    # Create the application profile
    created = await repository.create_application_profile(profile)
    
    # Verify creation succeeded
    assert created is not None, "Application profile creation should succeed"
    assert created.id == profile.id
    assert created.customer_id == profile.customer_id
    
    # Retrieve the application profile
    retrieved = await repository.get_application_profile_by_id(profile.id)
    
    # Property: Retrieved profile should not be None
    assert retrieved is not None, \
        f"Application profile {profile.id} should be retrievable after creation"
    
    # Property: Retrieved profile should have same ID
    assert retrieved.id == profile.id, \
        f"Retrieved profile ID {retrieved.id} should match original {profile.id}"
    
    # Property: Retrieved profile should have same customer_id
    assert retrieved.customer_id == profile.customer_id, \
        f"Retrieved customer_id {retrieved.customer_id} should match original {profile.customer_id}"
    
    # Property: Retrieved profile should have same name
    assert retrieved.name == profile.name, \
        f"Retrieved name '{retrieved.name}' should match original '{profile.name}'"
    
    # Property: Retrieved profile should have same type
    assert retrieved.type == profile.type, \
        f"Retrieved type '{retrieved.type}' should match original '{profile.type}'"
    
    # Property: Connection config should be preserved
    assert retrieved.connection_config is not None, \
        "Connection config should not be None"
    
    # Property: Connection config endpoint should match
    assert str(retrieved.connection_config.endpoint) == str(profile.connection_config.endpoint), \
        f"Retrieved endpoint should match original"
    
    # Property: Connection config timeout should match
    assert retrieved.connection_config.timeout == profile.connection_config.timeout, \
        f"Retrieved timeout {retrieved.connection_config.timeout} should match original {profile.connection_config.timeout}"
    
    # Property: Connection config retries should match
    assert retrieved.connection_config.retries == profile.connection_config.retries, \
        f"Retrieved retries {retrieved.connection_config.retries} should match original {profile.connection_config.retries}"
    
    # Property: Authentication config should match (if present)
    if profile.connection_config.authentication is not None:
        assert retrieved.connection_config.authentication is not None, \
            "Authentication should be preserved when present"
        assert retrieved.connection_config.authentication == profile.connection_config.authentication, \
            "Authentication config should match original"
    else:
        assert retrieved.connection_config.authentication is None, \
            "Authentication should be None when not provided"
    
    # Property: Custom headers should match (if present)
    if profile.connection_config.custom_headers is not None:
        assert retrieved.connection_config.custom_headers is not None, \
            "Custom headers should be preserved when present"
        assert retrieved.connection_config.custom_headers == profile.connection_config.custom_headers, \
            "Custom headers should match original"
    else:
        assert retrieved.connection_config.custom_headers is None, \
            "Custom headers should be None when not provided"


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    profile=application_profile_strategy(),
    app_type=st.sampled_from(["chatbot", "rag", "agent", "workflow", "custom"])
)
async def test_application_type_support(profile: ApplicationProfile, app_type: str):
    """
    Property 6: Application type support.
    
    **Validates: Requirements 2.3**
    
    For any valid application type (chatbot, RAG, agent, workflow, custom),
    registering an application of that type should succeed.
    """
    # Create mock database
    from unittest.mock import MagicMock
    mock_database = MagicMock()
    mock_database.applicationProfiles = MagicMock()
    
    repository = DataRepository(mock_database)
    
    # Update profile with the specific app type
    profile.type = app_type
    
    # Storage for the created profile document
    stored_doc = {}
    
    # Mock insert_one to store the profile
    async def mock_insert_one(doc):
        stored_doc.update(doc)
        result = MagicMock()
        result.inserted_id = doc["_id"]
        return result
    
    mock_database.applicationProfiles.insert_one = mock_insert_one
    
    # Property: Creating a profile with any valid application type should succeed
    try:
        created = await repository.create_application_profile(profile)
        assert created is not None, \
            f"Profile creation should succeed for application type '{app_type}'"
        assert created.type == app_type, \
            f"Created profile should have type '{app_type}'"
    except Exception as e:
        pytest.fail(f"Profile creation failed for valid application type '{app_type}': {e}")
    
    # Property: The stored document should contain the correct type
    assert "type" in stored_doc, "Stored document should contain 'type' field"
    assert stored_doc["type"] == app_type, \
        f"Stored type should be '{app_type}', got '{stored_doc.get('type')}'"
