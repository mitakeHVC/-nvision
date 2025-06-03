import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.api.main import app # Main FastAPI app
from src.data_models.client_preferences_models import ClientPreference, ClientPreferenceCreate, ClientPreferenceUpdate
from src.services.client_preference_service import ClientPreferenceService
from src.auth.dependencies import get_current_active_user # To override for auth
from src.auth.permissions import Permission # To check correct permissions are used

# Test client for making API requests
client = TestClient(app)

from src.auth.auth_service import AuthUser # Import AuthUser

USER_ID = "test_api_user_123" # This will be int for AuthUser if user_id is int
CLIENT_ID = str(uuid4())
PREFERENCE_ID = str(uuid4())

# MOCK_USER_MANAGER and MOCK_USER_VIEWER are now functions returning AuthUser instances
# Note: AuthUser expects user_id as int. For consistency, let's assume USER_ID should be an int.
# However, client_preferences_endpoints.py uses current_user.get("id", "unknown_user")
# and then str(user_id). This implies USER_ID in the mock dict was used as str.
# Let's make USER_ID an int for AuthUser and handle casting in endpoint tests if needed,
# or adjust AuthUser if user_id is universally string. Assuming AuthUser.user_id is the source of truth.
# The error was `AttributeError: 'dict' object has no attribute 'user_id'`, so an object is expected.

MOCK_USER_ID_INT_MANAGER = 123
MOCK_USER_ID_INT_VIEWER = 456


# Mock for get_current_active_user dependency
async def mock_get_manager_user() -> AuthUser:
    # The actual AuthUser class expects roles/permissions to be handled by PermissionManager,
    # not directly on the AuthUser object for the check_permission dependency.
    # The MOCK_USER_MANAGER dict had "roles", which get_current_active_user might have
    # been expected to process into an AuthUser-like object that PermissionManager uses.
    # For now, just returning an AuthUser. The key is that it has a `user_id` attribute.
    # The permission check itself relies on PermissionManager.has_permission(user_id, permission_enum)
    # The mock user's roles are used by the mock test client setup, not directly by this AuthUser object
    # unless the actual get_current_active_user enriches it.
    # For the failing test, having `user_id` attribute is key.
    return AuthUser(
        user_id=MOCK_USER_ID_INT_MANAGER,
        username="test_manager_user",
        email="manager@example.com",
        is_active=True
        # Roles are not part of AuthUser constructor, they are managed by PermissionManager
    )

async def mock_get_viewer_user() -> AuthUser:
    return AuthUser(
        user_id=MOCK_USER_ID_INT_VIEWER,
        username="test_viewer_user",
        email="viewer@example.com",
        is_active=True
    )


@pytest.fixture
def mock_preference_service():
    service_mock = MagicMock(spec=ClientPreferenceService)
    service_mock.create_preferences = AsyncMock()
    service_mock.get_preferences_by_client_id = AsyncMock()
    service_mock.get_preferences_by_id = AsyncMock()
    service_mock.update_preferences = AsyncMock()
    service_mock.delete_preferences = AsyncMock()
    return service_mock

from src.auth.permissions import PermissionManager # Import PermissionManager
from src.auth.dependencies import get_permission_manager # Import the dependency getter

@pytest.fixture(autouse=True) # Apply this fixture to all tests in this module
def override_dependencies_for_tests(mock_preference_service, monkeypatch):
    # Override get_current_active_user
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user # Default to manager

    # Override ClientPreferenceService
    app.dependency_overrides[ClientPreferenceService] = lambda: mock_preference_service

    # Get the actual permission manager and assign role to mock user
    # This needs to be done carefully if get_permission_manager itself has dependencies
    # or is a complex callable. Assuming it's straightforward or can be overridden.
    # A potentially cleaner way if get_permission_manager is complex is to also mock it,
    # and make the mocked PermissionManager behave as needed.
    # For now, let's try to get the real one and modify its state.

    # This direct call might not work if get_permission_manager itself is a complex dependency.
    # pm_instance = get_permission_manager() # This line might be problematic.
    # Instead, we should allow the FastAPI dependency system to resolve it once, then use it.
    # However, for testing, it's common to provide a test-specific PermissionManager
    # or ensure the default one is configured for tests.

    # Let's try to patch the PermissionManager instance that get_permission_manager returns
    # This is tricky because get_permission_manager is a simple function.
    # Alternative: The PermissionManager is likely a singleton or cached.
    # If PermissionManager is a global instance:
    # from src.auth.permissions import global_permission_manager # if it exists
    # global_permission_manager.assign_role_to_user(str(MOCK_USER_ID_INT_MANAGER), "manager")

    # Simplest approach for now: Assume PermissionManager is created fresh or can be accessed
    # and modified for the test session. This is a common challenge in testing DI.
    # A robust setup might involve a fixture that provides a pre-configured PermissionManager for tests.

    # Let's assume there's a way to get the permission manager instance used by dependencies.
    # If it's a singleton pattern or easily accessible:
    # current_pm = get_permission_manager() # This might create a new one each time if not singleton
    # current_pm.assign_role_to_user(str(MOCK_USER_ID_INT_MANAGER), "manager")
    # current_pm.assign_role_to_user(str(MOCK_USER_ID_INT_VIEWER), "viewer") # also for viewer

    # Given the structure, get_permission_manager likely instantiates PermissionManager().
    # We can mock `has_permission` on PermissionManager instances for simplicity in these tests,
    # or ensure the default PermissionManager (if it's consistently used) is pre-populated.

    # For now, let's assume that the default PermissionManager is used and roles are pre-defined.
    # The issue is that the user '123' is not *assigned* the 'manager' role in the PermissionManager.
    # The `MOCK_USER_MANAGER` has "roles": ["manager"], but this is just a dict, not AuthUser.
    # The AuthUser object from mock_get_manager_user doesn't inherently have roles in a way
    # that PermissionManager.has_permission would see without role assignment.

    # The `check_permission` dependency does:
    #   current_user: AuthUser = Depends(get_current_active_user),
    #   permission_manager: PermissionManager = Depends(get_permission_manager)
    #   if not permission_manager.has_permission(current_user.user_id, permission):
    #
    # So, `permission_manager` is the key. We need the instance it uses.
    # The easiest way to ensure this works for tests without complex DI mocking is to
    # ensure the default PermissionManager (which is created by get_permission_manager)
    # has the roles assigned. This happens if PermissionManager._setup_default_roles()
    # is comprehensive and we use user IDs that match users who would have these roles.
    # However, our mock users are new.

    # Let's patch PermissionManager.has_permission for simplicity in this test module,
    # acknowledging this is a shortcut for testing permissions.

    original_has_permission = PermissionManager.has_permission

    def mock_has_permission(self, user_id_from_auth_user, permission_enum_value):
        # `self` is the PermissionManager instance
        # `user_id_from_auth_user` is current_user.user_id
        # `permission_enum_value` is the Permission enum

        # Simulate role assignment for testing purposes
        # This is a broad mock; a more granular mock would be better for complex scenarios.
        if user_id_from_auth_user == MOCK_USER_ID_INT_MANAGER:
            # Assume manager has all client preference permissions
            if permission_enum_value in [
                Permission.CLIENT_PREFERENCES_CREATE,
                Permission.CLIENT_PREFERENCES_READ,
                Permission.CLIENT_PREFERENCES_UPDATE,
                Permission.CLIENT_PREFERENCES_DELETE,
            ]:
                return True
        elif user_id_from_auth_user == MOCK_USER_ID_INT_VIEWER:
            # Viewer has no client preference permissions for create/update/delete
             if permission_enum_value in [
                Permission.CLIENT_PREFERENCES_CREATE,
                Permission.CLIENT_PREFERENCES_UPDATE,
                Permission.CLIENT_PREFERENCES_DELETE,
            ]:
                return False
             elif permission_enum_value == Permission.CLIENT_PREFERENCES_READ:
                 return True # Assuming viewer can read
        return original_has_permission(self, user_id_from_auth_user, permission_enum_value)

    # original_has_permission = PermissionManager.has_permission # Not needed if we don't call it

    def mock_has_permission_for_tests(self_pm_instance, user_id_from_auth, permission_enum):
        # Manager user
        if user_id_from_auth == MOCK_USER_ID_INT_MANAGER:
            if permission_enum.name.startswith("CLIENT_PREFERENCES_"):
                return True
            # Fallback for manager for non-client-preference permissions if any were tested (currently not)
            # return original_has_permission(self_pm_instance, user_id_from_auth, permission_enum)

        # Viewer user
        elif user_id_from_auth == MOCK_USER_ID_INT_VIEWER:
            if permission_enum == Permission.CLIENT_PREFERENCES_READ:
                return True
            # Explicitly deny other client preference permissions for viewer
            if permission_enum.name.startswith("CLIENT_PREFERENCES_") and \
               permission_enum != Permission.CLIENT_PREFERENCES_READ:
                return False
            # Fallback for viewer for non-client-preference permissions
            # return original_has_permission(self_pm_instance, user_id_from_auth, permission_enum)

        # Default deny for any other user_id or unhandled permission for these specific tests
        return False

    monkeypatch.setattr(PermissionManager, "has_permission", mock_has_permission_for_tests)

    yield

    monkeypatch.undo() # Revert the patch
    app.dependency_overrides = {} # Clear overrides after tests


# --- Test Cases ---

def test_create_client_preferences_success(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user
    create_payload = {"client_id": CLIENT_ID, "preferences_payload": {"theme": "dark"}}

    mock_preference_service.create_preferences.return_value = ClientPreference(
        id=PREFERENCE_ID, client_id=CLIENT_ID, preferences_payload={"theme": "dark"},
        created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )

    response = client.post("/api/v1/client-preferences/", json=create_payload)

    assert response.status_code == 201
    assert response.json()["client_id"] == CLIENT_ID
    assert response.json()["preferences_payload"] == {"theme": "dark"}
    mock_preference_service.create_preferences.assert_called_once()
    call_args, _ = mock_preference_service.create_preferences.call_args
    assert call_args[0].client_id == CLIENT_ID
    # Ensure created_by is passed correctly. AuthUser.user_id is int.
    # The endpoint does str(user_id)
    assert call_args[1] == str(MOCK_USER_ID_INT_MANAGER)


def test_create_client_preferences_unauthorized(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_viewer_user # Viewer lacks create perm
    create_payload = {"client_id": CLIENT_ID, "preferences_payload": {"theme": "dark"}}

    # At this point, the require_permission decorator should raise a 403
    # before it even hits the service mock, if permissions are correctly set up.
    # The PermissionManager should deny based on 'viewer' role not having CLIENT_PREFERENCES_CREATE.

    response = client.post("/api/v1/client-preferences/", json=create_payload)

    assert response.status_code == 403 # Forbidden
    mock_preference_service.create_preferences.assert_not_called()


def test_get_preferences_by_client_id_success(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user # Or any user with read
    mock_preference_service.get_preferences_by_client_id.return_value = ClientPreference(
        id=PREFERENCE_ID, client_id=CLIENT_ID, preferences_payload={"lang": "en"}
    )

    response = client.get(f"/api/v1/client-preferences/{CLIENT_ID}")

    assert response.status_code == 200
    assert response.json()["client_id"] == CLIENT_ID
    mock_preference_service.get_preferences_by_client_id.assert_called_once_with(CLIENT_ID)


def test_get_preferences_by_client_id_not_found(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user

    # Import core exception for mocking service behavior
    from src.core.exceptions import NotFoundException as CoreNotFoundException
    mock_preference_service.get_preferences_by_client_id.side_effect = CoreNotFoundException("Not found")

    response = client.get(f"/api/v1/client-preferences/{CLIENT_ID}")

    # The endpoint itself raises HTTPException(404) if service returns None or raises NotFoundException
    assert response.status_code == 404


def test_get_preferences_by_id_success(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user
    mock_preference_service.get_preferences_by_id.return_value = ClientPreference(
        id=PREFERENCE_ID, client_id=CLIENT_ID, preferences_payload={"timezone": "UTC"}
    )

    response = client.get(f"/api/v1/client-preferences/id/{PREFERENCE_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == PREFERENCE_ID
    mock_preference_service.get_preferences_by_id.assert_called_once_with(PREFERENCE_ID)


def test_update_client_preferences_success(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user
    update_payload = {"preferences_payload": {"theme": "light"}}
    mock_preference_service.update_preferences.return_value = ClientPreference(
        id=PREFERENCE_ID, client_id=CLIENT_ID, preferences_payload={"theme": "light"}
    )

    response = client.put(f"/api/v1/client-preferences/{PREFERENCE_ID}", json=update_payload)

    assert response.status_code == 200
    assert response.json()["preferences_payload"]["theme"] == "light"
    # Check that service method was called with ClientPreferenceUpdate model if that's the type hint
    # called_args, _ = mock_preference_service.update_preferences.call_args
    # assert isinstance(called_args[1], ClientPreferenceUpdate)


def test_update_client_preferences_forbidden(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_viewer_user # Viewer lacks update perm
    update_payload = {"preferences_payload": {"theme": "light"}}

    response = client.put(f"/api/v1/client-preferences/{PREFERENCE_ID}", json=update_payload)

    assert response.status_code == 403 # Forbidden
    mock_preference_service.update_preferences.assert_not_called()


def test_delete_client_preferences_success(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user
    mock_preference_service.delete_preferences.return_value = True

    response = client.delete(f"/api/v1/client-preferences/{PREFERENCE_ID}")

    assert response.status_code == 204
    mock_preference_service.delete_preferences.assert_called_once_with(PREFERENCE_ID, deleted_by=str(MOCK_USER_ID_INT_MANAGER))


def test_delete_client_preferences_not_found(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user
    # Import core exception for mocking service behavior
    from src.core.exceptions import NotFoundException as CoreNotFoundException
    mock_preference_service.delete_preferences.side_effect = CoreNotFoundException("Not found to delete")

    response = client.delete(f"/api/v1/client-preferences/{PREFERENCE_ID}")

    assert response.status_code == 404
    mock_preference_service.delete_preferences.assert_called_once_with(PREFERENCE_ID, deleted_by=str(MOCK_USER_ID_INT_MANAGER))


def test_delete_client_preferences_forbidden(mock_preference_service: MagicMock):
    app.dependency_overrides[get_current_active_user] = mock_get_viewer_user # Viewer lacks delete perm

    response = client.delete(f"/api/v1/client-preferences/{PREFERENCE_ID}")

    assert response.status_code == 403 # Forbidden
    mock_preference_service.delete_preferences.assert_not_called()

# Further tests:
# - Invalid request payloads (e.g., missing client_id for create) -> 422 Unprocessable Entity
# - Service layer raising other specific exceptions (ServiceException, DatabaseException)
#   and ensuring they are translated to correct HTTP status codes (400, 500).
# - Test with a user that has some but not all permissions.
# - Test the `current_user`'s ID is correctly passed as `created_by` or `updated_by`.

@pytest.mark.parametrize("payload, expected_status", [
    ({"preferences_payload": {"key": "value"}}, 422), # Missing client_id
    ({"client_id": CLIENT_ID}, 422), # Missing preferences_payload
])
def test_create_client_preferences_invalid_payload(mock_preference_service: MagicMock, payload: dict, expected_status: int):
    app.dependency_overrides[get_current_active_user] = mock_get_manager_user
    response = client.post("/api/v1/client-preferences/", json=payload)
    assert response.status_code == expected_status
    mock_preference_service.create_preferences.assert_not_called()
