import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.data_models.client_preferences_models import ClientPreference, ClientPreferenceCreate, ClientPreferenceUpdate
from src.services.client_preference_service import ClientPreferenceService
from src.repositories.client_preference_repository import ClientPreferenceRepository
from src.core.exceptions import ServiceException, NotFoundException # Changed to core.exceptions

USER_ID = "test_user_123"

@pytest.fixture
def mock_neo4j_connector():
    connector = MagicMock()
    # If your connector has an async close method that needs to be awaited:
    # connector.close = AsyncMock()
    return connector

@pytest.fixture
def mock_repository(mock_neo4j_connector):
    # Patch the __init__ of ClientPreferenceRepository to prevent it from
    # trying to initialize constraints if that's problematic for unit tests.
    with patch.object(ClientPreferenceRepository, '_ensure_constraints', return_value=None):
        repo = ClientPreferenceRepository(neo4j_connector=mock_neo4j_connector)
        repo.create = AsyncMock()
        repo.get_by_client_id = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        return repo

@pytest.fixture
def preference_service(mock_repository):
    # We need to ensure that when ClientPreferenceService is instantiated,
    # it uses our mock_repository. We can patch the ClientPreferenceRepository constructor
    # or patch where ClientPreferenceRepository is instantiated within the service.
    # For simplicity, let's assume the service takes the repo as a constructor arg,
    # or we can patch its .repository attribute directly after instantiation.

    # Patch the Neo4jConnector instantiation within the service to avoid real DB connection
    with patch('src.services.client_preference_service.Neo4jConnector') as MockNeo4jConnector:
        mock_connector_instance = MockNeo4jConnector.return_value

        # If ClientPreferenceRepository is instantiated inside ClientPreferenceService,
        # we need to ensure it gets the mock_connector_instance or is replaced by mock_repository.
        with patch('src.services.client_preference_service.ClientPreferenceRepository') as MockRepoClass:
            MockRepoClass.return_value = mock_repository
            service = ClientPreferenceService()
            # service.repository = mock_repository # Alternative: directly assign if structure allows
            return service


@pytest.mark.asyncio
async def test_create_preferences_success(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    client_id = str(uuid4())
    create_data = ClientPreferenceCreate(
        client_id=client_id,
        preferences_payload={"key": "value"}
    )
    expected_id = str(uuid4())
    mock_repository.get_by_client_id.return_value = None # No existing preference
    mock_repository.create.return_value = ClientPreference(
        id=expected_id,
        client_id=client_id,
        preferences_payload={"key": "value"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    result = await preference_service.create_preferences(create_data, created_by=USER_ID)

    assert result is not None
    assert result.client_id == client_id
    assert result.id == expected_id
    mock_repository.create.assert_called_once_with(create_data, USER_ID)
    mock_repository.get_by_client_id.assert_called_once_with(client_id)


@pytest.mark.asyncio
async def test_create_preferences_already_exists(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    client_id = str(uuid4())
    create_data = ClientPreferenceCreate(client_id=client_id, preferences_payload={"key": "value"})

    mock_repository.get_by_client_id.return_value = ClientPreference(
        id=str(uuid4()), client_id=client_id, preferences_payload={}
    ) # Simulate existing preference

    with pytest.raises(ServiceException) as excinfo:
        await preference_service.create_preferences(create_data, created_by=USER_ID)
    assert f"Client preferences for client_id '{client_id}' already exist" in str(excinfo.value)
    mock_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_preferences_by_client_id_found(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    client_id = str(uuid4())
    expected_pref = ClientPreference(id=str(uuid4()), client_id=client_id, preferences_payload={"foo": "bar"})
    mock_repository.get_by_client_id.return_value = expected_pref

    result = await preference_service.get_preferences_by_client_id(client_id)

    assert result == expected_pref
    mock_repository.get_by_client_id.assert_called_once_with(client_id)


@pytest.mark.asyncio
async def test_get_preferences_by_client_id_not_found(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    client_id = str(uuid4())
    mock_repository.get_by_client_id.return_value = None

    result = await preference_service.get_preferences_by_client_id(client_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_preferences_by_id_found(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    pref_id = str(uuid4())
    expected_pref = ClientPreference(id=pref_id, client_id=str(uuid4()), preferences_payload={"foo": "bar"})
    mock_repository.get_by_id.return_value = expected_pref

    result = await preference_service.get_preferences_by_id(pref_id)

    assert result == expected_pref
    mock_repository.get_by_id.assert_called_once_with(pref_id)

@pytest.mark.asyncio
async def test_get_preferences_by_id_invalid_format(preference_service: ClientPreferenceService):
    with pytest.raises(ServiceException, match="Invalid preference_id format"):
        await preference_service.get_preferences_by_id("invalid-uuid-format")


@pytest.mark.asyncio
async def test_update_preferences_success(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    pref_id = str(uuid4())
    update_data = ClientPreferenceUpdate(preferences_payload={"new_key": "new_value"})

    # Mock that the preference exists
    mock_repository.get_by_id.return_value = ClientPreference(id=pref_id, client_id="some_client", preferences_payload={})

    mock_repository.update.return_value = ClientPreference(
        id=pref_id, client_id="some_client", preferences_payload=update_data.preferences_payload
    )

    result = await preference_service.update_preferences(pref_id, update_data, updated_by=USER_ID)

    assert result is not None
    assert result.preferences_payload == {"new_key": "new_value"}
    mock_repository.update.assert_called_once_with(pref_id, update_data, USER_ID)


@pytest.mark.asyncio
async def test_update_preferences_not_found(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    pref_id = str(uuid4())
    update_data = ClientPreferenceUpdate(preferences_payload={"new_key": "new_value"})
    mock_repository.get_by_id.return_value = None # Simulate not found

    with pytest.raises(NotFoundException):
        await preference_service.update_preferences(pref_id, update_data, updated_by=USER_ID)
    mock_repository.update.assert_not_called()


@pytest.mark.asyncio
async def test_delete_preferences_success(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    pref_id = str(uuid4())
    mock_repository.get_by_id.return_value = ClientPreference(id=pref_id, client_id="client", preferences_payload={}) # Exists
    mock_repository.delete.return_value = True

    result = await preference_service.delete_preferences(pref_id, deleted_by=USER_ID)

    assert result is True
    mock_repository.delete.assert_called_once_with(pref_id, USER_ID)


@pytest.mark.asyncio
async def test_delete_preferences_not_found(preference_service: ClientPreferenceService, mock_repository: ClientPreferenceRepository):
    pref_id = str(uuid4())
    mock_repository.get_by_id.return_value = None # Simulate not found

    with pytest.raises(NotFoundException):
        await preference_service.delete_preferences(pref_id, deleted_by=USER_ID)
    mock_repository.delete.assert_not_called()

@pytest.mark.asyncio
async def test_close_db_connection_called(preference_service: ClientPreferenceService, mock_neo4j_connector: MagicMock):
    # Ensure the service's connector is the one we're checking
    preference_service.neo4j_connector = mock_neo4j_connector
    mock_neo4j_connector.close = AsyncMock() # Ensure it's an AsyncMock for await

    await preference_service.close_db_connection()

    # Check if Neo4jConnector's close was called if it exists and has a close method
    if hasattr(mock_neo4j_connector, 'close'):
        mock_neo4j_connector.close.assert_called_once()

@pytest.mark.asyncio
async def test_service_initialization_no_connector(): # Removed mock_repository fixture
    # Test service behavior when Neo4jConnector fails to initialize
    with patch('src.services.client_preference_service.Neo4jConnector', side_effect=Exception("Connection failed")):
        # Instantiate service directly to test its __init__ logic when connector fails.
        # This setup does not involve the 'preference_service' fixture, so ClientPreferenceRepository
        # will not be automatically replaced by mock_repository unless explicitly patched here (which we don't want for this test).
        service = ClientPreferenceService()
        assert service.repository is None # Repository should be None if connector fails

        # Verify that attempting to use the service raises an appropriate error
        with pytest.raises(ServiceException, match="ClientPreferenceService is not properly configured"):
           await service.get_preferences_by_id(str(uuid4()))


# Add more tests for edge cases, error handling, specific payload contents, etc.
