import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime

from src.api.main import app # Main FastAPI app
from src.data_models.suggestion_models import Suggestion, ActionPlan, ActionPlanStep, SuggestionWithActionPlan
# ClientPreference not directly used in this test file after mocks, but good to keep if needed for future payload construction
# from src.data_models.client_preferences_models import ClientPreference
from src.services.suggestion_service import SuggestionService
from src.services.analytics_service import AnalyticsService # Added import
from src.services.client_preference_service import ClientPreferenceService # Added import
from src.auth.dependencies import get_current_active_user
from src.auth.auth_service import AuthUser # For mock user type
from src.auth.permissions import Permission, PermissionManager # For mocking permissions

# Test client
client = TestClient(app)

# Mock user IDs
MOCK_USER_ID_MANAGER = 789
MOCK_USER_ID_ANALYST = 790
MOCK_USER_ID_NO_PERMS = 791

# Mock data
CLIENT_ID = str(uuid.uuid4())
SUGGESTION_ID = str(uuid.uuid4())
ACTION_PLAN_ID = str(uuid.uuid4())
STEP_ID = str(uuid.uuid4())

# Mock AuthUser instances
mock_manager_user = AuthUser(user_id=MOCK_USER_ID_MANAGER, username="suggestion_manager", email="sm@example.com", is_active=True)
mock_analyst_user = AuthUser(user_id=MOCK_USER_ID_ANALYST, username="suggestion_analyst", email="sa@example.com", is_active=True)
mock_no_perms_user = AuthUser(user_id=MOCK_USER_ID_NO_PERMS, username="no_perms_user", email="np@example.com", is_active=True)


@pytest.fixture
def mock_suggestion_service():
    service = MagicMock(spec=SuggestionService)
    service.generate_suggestions = AsyncMock()
    service.get_suggestion_details = AsyncMock()
    service.update_action_plan_step_status = AsyncMock()
    return service

@pytest.fixture
def mock_analytics_service_for_sugg_api(): # Renamed to avoid conflict if used elsewhere
    service = MagicMock(spec=AnalyticsService)
    service.get_comprehensive_dashboard = AsyncMock()
    return service

@pytest.fixture
def mock_client_preference_service_for_sugg_api(): # Renamed
    service = MagicMock(spec=ClientPreferenceService)
    service.get_preferences_by_client_id = AsyncMock()
    return service

@pytest.fixture(autouse=True)
def override_suggestion_dependencies(
    mock_suggestion_service: MagicMock,
    mock_analytics_service_for_sugg_api: MagicMock,
    mock_client_preference_service_for_sugg_api: MagicMock
):
    # Import the actual dependency functions from the endpoint module
    from src.api.routers.api_v1.endpoints.suggestions import (
        get_analytics_service_dependency,
        get_client_preference_service_dependency,
        get_suggestion_service # This is the top-level one we want to ensure uses mocks
    )

    # Override the functions that SuggestionService's dependencies rely on
    app.dependency_overrides[get_analytics_service_dependency] = lambda: mock_analytics_service_for_sugg_api
    app.dependency_overrides[get_client_preference_service_dependency] = lambda: mock_client_preference_service_for_sugg_api

    # We are also mocking the SuggestionService itself for these API tests,
    # so the direct instantiation of SuggestionService in get_suggestion_service
    # will use the already-mocked analytics_service and client_preference_service from above.
    # However, the API endpoint depends on `get_suggestion_service`.
    # If we want to ensure the SuggestionService used by the endpoint is our mock_suggestion_service,
    # we should override get_suggestion_service.
    app.dependency_overrides[get_suggestion_service] = lambda: mock_suggestion_service
    # Or, if we want to test the real get_suggestion_service wiring but with its *own* dependencies mocked (which we did above):
    # app.dependency_overrides[SuggestionService] = SuggestionService
    # This would mean get_suggestion_service runs, gets the mocked sub-services, and creates a real SuggestionService.
    # For API tests, mocking the target service (SuggestionService) directly is usually preferred for isolation.

    yield
    app.dependency_overrides = {}

# Store original PermissionManager.has_permission for restoration
original_has_permission = PermissionManager.has_permission

def mock_permissions_for_suggestions(monkeypatch, user_to_return: AuthUser, permissions_to_grant: list):
    # Override get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: user_to_return

    def mock_has_permission(self_pm, user_id_from_auth, permission_enum_value):
        if user_id_from_auth == user_to_return.user_id:
            if permission_enum_value in permissions_to_grant:
                return True
        return False # Deny by default for this simplified mock

    monkeypatch.setattr(PermissionManager, "has_permission", mock_has_permission)

@pytest.fixture
def manager_with_suggestion_perms(monkeypatch):
    mock_permissions_for_suggestions(monkeypatch, mock_manager_user, [Permission.SUGGESTION_READ, Permission.ACTION_PLAN_UPDATE])

@pytest.fixture
def analyst_with_suggestion_read_perms(monkeypatch):
    mock_permissions_for_suggestions(monkeypatch, mock_analyst_user, [Permission.SUGGESTION_READ])

@pytest.fixture
def user_without_suggestion_perms(monkeypatch):
    mock_permissions_for_suggestions(monkeypatch, mock_no_perms_user, [])


# --- Test Cases ---

def test_get_suggestions_for_client_success(mock_suggestion_service: MagicMock, manager_with_suggestion_perms):
    mock_suggestion = Suggestion(id=SUGGESTION_ID, title="Test Suggestion", description="Desc", source_analysis_type="test")
    mock_action_plan = ActionPlan(id=ACTION_PLAN_ID, suggestion_id=SUGGESTION_ID, title="Test Plan", overview="Overview")
    mock_response_data = [SuggestionWithActionPlan(suggestion=mock_suggestion, action_plan=mock_action_plan)]
    mock_suggestion_service.generate_suggestions.return_value = mock_response_data

    response = client.get(f"/api/v1/suggestions/client/{CLIENT_ID}?days=60")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["suggestion"]["id"] == SUGGESTION_ID
    mock_suggestion_service.generate_suggestions.assert_called_once_with(client_id=CLIENT_ID, days=60)

def test_get_suggestions_for_client_unauthorized(mock_suggestion_service: MagicMock, user_without_suggestion_perms):
    response = client.get(f"/api/v1/suggestions/client/{CLIENT_ID}")
    assert response.status_code == 403
    mock_suggestion_service.generate_suggestions.assert_not_called()

def test_get_suggestion_details_success(mock_suggestion_service: MagicMock, analyst_with_suggestion_read_perms):
    mock_suggestion = Suggestion(id=SUGGESTION_ID, title="Detail Suggestion", description="Detail Desc", source_analysis_type="detail_test")
    mock_response_data = SuggestionWithActionPlan(suggestion=mock_suggestion)
    mock_suggestion_service.get_suggestion_details.return_value = mock_response_data

    response = client.get(f"/api/v1/suggestions/{SUGGESTION_ID}")

    assert response.status_code == 200
    assert response.json()["suggestion"]["id"] == SUGGESTION_ID
    mock_suggestion_service.get_suggestion_details.assert_called_once_with(suggestion_id=SUGGESTION_ID)

def test_get_suggestion_details_not_found(mock_suggestion_service: MagicMock, manager_with_suggestion_perms):
    mock_suggestion_service.get_suggestion_details.return_value = None
    response = client.get(f"/api/v1/suggestions/{str(uuid.uuid4())}") # Non-existent ID
    assert response.status_code == 404 # APINotFoundError is raised by endpoint

def test_update_action_plan_step_status_success(mock_suggestion_service: MagicMock, manager_with_suggestion_perms):
    updated_status = "in_progress"
    mock_action_plan = ActionPlan(id=ACTION_PLAN_ID, suggestion_id=SUGGESTION_ID, title="Updated Plan", overview="Updated Overview", overall_status=updated_status)
    mock_suggestion_service.update_action_plan_step_status.return_value = mock_action_plan

    payload = {"new_status": updated_status}
    response = client.put(f"/api/v1/suggestions/action-plans/{ACTION_PLAN_ID}/steps/{STEP_ID}/status", json=payload)

    assert response.status_code == 200
    assert response.json()["id"] == ACTION_PLAN_ID
    assert response.json()["overall_status"] == updated_status # Assuming service updates this too
    mock_suggestion_service.update_action_plan_step_status.assert_called_once_with(action_plan_id=ACTION_PLAN_ID, step_id=STEP_ID, new_status=updated_status)

def test_update_action_plan_step_status_unauthorized(mock_suggestion_service: MagicMock, analyst_with_suggestion_read_perms): # Analyst cannot update
    payload = {"new_status": "completed"}
    response = client.put(f"/api/v1/suggestions/action-plans/{ACTION_PLAN_ID}/steps/{STEP_ID}/status", json=payload)
    assert response.status_code == 403
    mock_suggestion_service.update_action_plan_step_status.assert_not_called()

def test_update_action_plan_step_status_not_found(mock_suggestion_service: MagicMock, manager_with_suggestion_perms):
    mock_suggestion_service.update_action_plan_step_status.return_value = None
    payload = {"new_status": "completed"}
    response = client.put(f"/api/v1/suggestions/action-plans/{str(uuid.uuid4())}/steps/{str(uuid.uuid4())}/status", json=payload)
    assert response.status_code == 404

def test_update_action_plan_step_status_invalid_payload(mock_suggestion_service: MagicMock, manager_with_suggestion_perms):
    payload = {"new_status": "   "} # Empty or whitespace only
    response = client.put(f"/api/v1/suggestions/action-plans/{ACTION_PLAN_ID}/steps/{STEP_ID}/status", json=payload)
    # Pydantic v2 by default does not allow empty strings for `str` fields unless explicitly Optional or default is ""
    # The model is `new_status: str`. If payload is `{"new_status": " "}`, pydantic might pass it.
    # My custom validation `if not status_update.new_status.strip():` should then catch it, raising APIValidationError.
    # APIValidationError is configured to return HTTP 422.
    assert response.status_code == 422
    assert "New status cannot be empty" in response.json()["detail"]["message"] # Custom error message
    mock_suggestion_service.update_action_plan_step_status.assert_not_called()

# Cleanup monkeypatch after all tests in this module are done
@pytest.fixture(scope="module", autouse=True)
def cleanup_monkeypatch():
    yield
    PermissionManager.has_permission = original_has_permission
    app.dependency_overrides = {}
