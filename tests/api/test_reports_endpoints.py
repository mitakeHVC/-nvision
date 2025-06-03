import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timedelta

from src.api.main import app # Main FastAPI app
from src.data_models.reporting_models import EffectivenessReport, MetricValue
# Request model for one of the endpoints
from src.api.routers.api_v1.endpoints.reports import ReportGenerationRequest
from src.services.effectiveness_reporting_service import EffectivenessReportingService
from src.services.analytics_service import AnalyticsService # For DI mocking
from src.repositories.suggestion_repository import SuggestionRepository # For DI mocking
from src.auth.dependencies import get_current_active_user
from src.auth.auth_service import AuthUser
from src.auth.permissions import Permission, PermissionManager

client = TestClient(app)

# Mock user IDs
MOCK_USER_ID_MANAGER = 888
MOCK_USER_ID_ANALYST = 889 # Different from suggestion tests to avoid potential conflicts if run together
MOCK_USER_ID_NO_PERMS = 890

# Mock data IDs
ACTION_PLAN_ID = str(uuid.uuid4())
REPORT_ID = str(uuid.uuid4())

# Mock AuthUser instances
mock_manager_user = AuthUser(user_id=MOCK_USER_ID_MANAGER, username="report_manager", email="rm@example.com", is_active=True)
mock_analyst_user = AuthUser(user_id=MOCK_USER_ID_ANALYST, username="report_analyst", email="ra@example.com", is_active=True)
mock_no_perms_user = AuthUser(user_id=MOCK_USER_ID_NO_PERMS, username="report_no_perms", email="rnp@example.com", is_active=True)


@pytest.fixture
def mock_effectiveness_reporting_service():
    service = MagicMock(spec=EffectivenessReportingService)
    service.generate_report_for_action_plan = AsyncMock()
    service.get_report_by_id = AsyncMock()
    service.list_reports_for_action_plan = AsyncMock()
    return service

@pytest.fixture
def mock_analytics_service_for_report_api():
    return MagicMock(spec=AnalyticsService)

@pytest.fixture
def mock_suggestion_repo_for_report_api():
    return MagicMock(spec=SuggestionRepository)

@pytest.fixture(autouse=True)
def override_reporting_dependencies(
    mock_effectiveness_reporting_service: MagicMock,
    mock_analytics_service_for_report_api: MagicMock,
    mock_suggestion_repo_for_report_api: MagicMock
):
    from src.api.routers.api_v1.endpoints.reports import (
        get_effectiveness_reporting_service,
        get_analytics_service_dependency,
        get_suggestion_repository_dependency
    )
    app.dependency_overrides[get_effectiveness_reporting_service] = lambda: mock_effectiveness_reporting_service
    app.dependency_overrides[get_analytics_service_dependency] = lambda: mock_analytics_service_for_report_api
    app.dependency_overrides[get_suggestion_repository_dependency] = lambda: mock_suggestion_repo_for_report_api
    yield
    app.dependency_overrides = {}

# Store original PermissionManager.has_permission for restoration
original_has_permission_reports = PermissionManager.has_permission

def mock_permissions_for_reports(monkeypatch, user_to_return: AuthUser, permissions_to_grant: list):
    app.dependency_overrides[get_current_active_user] = lambda: user_to_return
    def mock_has_permission(self_pm, user_id_from_auth, permission_enum_value):
        if user_id_from_auth == user_to_return.user_id:
            if permission_enum_value in permissions_to_grant:
                return True
        return False
    monkeypatch.setattr(PermissionManager, "has_permission", mock_has_permission)

@pytest.fixture
def manager_with_report_perms(monkeypatch):
    mock_permissions_for_reports(monkeypatch, mock_manager_user, [Permission.REPORT_READ])

@pytest.fixture
def analyst_with_report_perms(monkeypatch):
    mock_permissions_for_reports(monkeypatch, mock_analyst_user, [Permission.REPORT_READ])

@pytest.fixture
def user_without_report_perms(monkeypatch):
    mock_permissions_for_reports(monkeypatch, mock_no_perms_user, [])


# --- Test Cases ---

def test_generate_effectiveness_report_success(mock_effectiveness_reporting_service: MagicMock, manager_with_report_perms):
    now = datetime.utcnow()
    report_data = ReportGenerationRequest(
        reporting_period_start=now - timedelta(days=30),
        reporting_period_end=now
    )
    mock_report = EffectivenessReport(
        id=REPORT_ID, report_title="Test Report", action_plan_id=ACTION_PLAN_ID, action_plan_title="AP Title",
        reporting_period_start=report_data.reporting_period_start, reporting_period_end=report_data.reporting_period_end,
        summary="Great success!", generated_by=str(MOCK_USER_ID_MANAGER)
    )
    mock_effectiveness_reporting_service.generate_report_for_action_plan.return_value = mock_report

    response = client.post(f"/api/v1/reports/effectiveness/action-plan/{ACTION_PLAN_ID}", json=json.loads(report_data.model_dump_json()))

    assert response.status_code == 201
    assert response.json()["id"] == REPORT_ID
    mock_effectiveness_reporting_service.generate_report_for_action_plan.assert_called_once_with(
        action_plan_id=ACTION_PLAN_ID,
        reporting_period_start=report_data.reporting_period_start,
        reporting_period_end=report_data.reporting_period_end,
        baseline_period_start=None,
        baseline_period_end=None,
        generated_by=str(MOCK_USER_ID_MANAGER)
    )

def test_generate_report_unauthorized(mock_effectiveness_reporting_service: MagicMock, user_without_report_perms):
    now = datetime.utcnow()
    report_data = ReportGenerationRequest(reporting_period_start=now - timedelta(days=30), reporting_period_end=now)
    response = client.post(f"/api/v1/reports/effectiveness/action-plan/{ACTION_PLAN_ID}", json=json.loads(report_data.model_dump_json()))
    assert response.status_code == 403
    mock_effectiveness_reporting_service.generate_report_for_action_plan.assert_not_called()

def test_generate_report_action_plan_not_found(mock_effectiveness_reporting_service: MagicMock, manager_with_report_perms):
    now = datetime.utcnow()
    report_data = ReportGenerationRequest(reporting_period_start=now - timedelta(days=30), reporting_period_end=now)
    # Service raises CoreNotFoundException, decorator converts to APINotFoundError (404)
    mock_effectiveness_reporting_service.generate_report_for_action_plan.side_effect = CoreNotFoundException("Action plan not found")

    response = client.post(f"/api/v1/reports/effectiveness/action-plan/{ACTION_PLAN_ID}", json=json.loads(report_data.model_dump_json()))
    assert response.status_code == 404


def test_get_effectiveness_report_by_id_success(mock_effectiveness_reporting_service: MagicMock, analyst_with_report_perms):
    mock_report = EffectivenessReport(
        id=REPORT_ID, report_title="Specific Report", action_plan_id=ACTION_PLAN_ID, action_plan_title="AP Title",
        reporting_period_start=datetime.utcnow(), reporting_period_end=datetime.utcnow(), summary="Details"
    )
    mock_effectiveness_reporting_service.get_report_by_id.return_value = mock_report

    response = client.get(f"/api/v1/reports/effectiveness/{REPORT_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == REPORT_ID
    mock_effectiveness_reporting_service.get_report_by_id.assert_called_once_with(report_id=REPORT_ID)

def test_get_effectiveness_report_by_id_not_found(mock_effectiveness_reporting_service: MagicMock, manager_with_report_perms):
    mock_effectiveness_reporting_service.get_report_by_id.return_value = None
    response = client.get(f"/api/v1/reports/effectiveness/{str(uuid.uuid4())}")
    assert response.status_code == 404

def test_list_reports_for_action_plan_success(mock_effectiveness_reporting_service: MagicMock, analyst_with_report_perms):
    mock_report = EffectivenessReport(
        id=REPORT_ID, report_title="Listed Report", action_plan_id=ACTION_PLAN_ID, action_plan_title="AP Title",
        reporting_period_start=datetime.utcnow(), reporting_period_end=datetime.utcnow(), summary="List item"
    )
    mock_effectiveness_reporting_service.list_reports_for_action_plan.return_value = [mock_report]

    response = client.get(f"/api/v1/reports/effectiveness/action-plan/{ACTION_PLAN_ID}/list")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == REPORT_ID
    mock_effectiveness_reporting_service.list_reports_for_action_plan.assert_called_once_with(action_plan_id=ACTION_PLAN_ID)

def test_list_reports_for_action_plan_empty(mock_effectiveness_reporting_service: MagicMock, manager_with_report_perms):
    mock_effectiveness_reporting_service.list_reports_for_action_plan.return_value = []
    response = client.get(f"/api/v1/reports/effectiveness/action-plan/{ACTION_PLAN_ID}/list")
    assert response.status_code == 200
    assert response.json() == []


# Cleanup monkeypatch after all tests in this module are done
@pytest.fixture(scope="module", autouse=True)
def cleanup_reporting_monkeypatch():
    yield
    PermissionManager.has_permission = original_has_permission_reports
    app.dependency_overrides = {}

# Need to import CoreNotFoundException for one of the tests
from src.core.exceptions import NotFoundException as CoreNotFoundException
import json # For serializing ReportGenerationRequest
