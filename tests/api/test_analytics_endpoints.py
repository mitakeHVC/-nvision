import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException # Added for mock_require_analytics_permission

from src.api.main import app # Corrected import for the FastAPI app
from src.services.analytics_service import AnalyticsService
from src.auth.permissions import Permission
# Make sure get_current_active_user is correctly imported if it's to be overridden
from src.auth.dependencies import get_current_active_user

# Test client
client = TestClient(app)

# Mock user with appropriate permissions
MOCK_USER = {
    "id": "test_user_id",
    "username": "test_analytics_user",
    "email": "test@example.com",
    "is_active": True,
    "roles": ["analyst"],  # Assuming 'analyst' role has ANALYTICS_READ
}

# Mock for get_current_active_user dependency
async def mock_get_current_active_user_with_analytics_permission():
    return MOCK_USER

# Mock for require_permission dependency
def mock_require_analytics_permission(permission: Permission):
    async def mock_dependency():
        if permission == Permission.ANALYTICS_READ and "analyst" in MOCK_USER["roles"]:
            return True # User has permission
        raise HTTPException(status_code=403, detail="Not authorized")
    return mock_dependency


@pytest.fixture(scope="module", autouse=True)
def override_auth_dependencies():
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user_with_analytics_permission
    # It's tricky to override require_permission directly in this manner for all tests
    # because it's a function that returns a dependency.
    # For more granular control, individual test functions might need to patch it
    # or we ensure the MOCK_USER has the correct roles/permissions by default.
    # For now, we rely on the get_current_active_user mock and the user's roles.
    yield
    app.dependency_overrides = {}


# Test cases for analytics endpoints
@patch("src.services.analytics_service.AnalyticsService.get_comprehensive_dashboard", new_callable=AsyncMock)
async def test_get_comprehensive_dashboard_success(mock_get_dashboard):
    mock_get_dashboard.return_value = {"data": "comprehensive dashboard data"}

    # Override require_permission for this specific test if needed, or ensure mock_user has permissions
    # For this example, assuming MOCK_USER has the 'analyst' role which grants ANALYTICS_READ by application logic

    response = client.get("/api/v1/analytics/dashboard?days=30")

    assert response.status_code == 200, response.text
    assert response.json() == {"data": "comprehensive dashboard data"}
    mock_get_dashboard.assert_called_once_with(days=30)


@patch("src.services.analytics_service.AnalyticsService.get_sales_analytics", new_callable=AsyncMock)
async def test_get_sales_analytics_success(mock_get_sales):
    mock_get_sales.return_value = {"data": "sales analytics data"}
    response = client.get("/api/v1/analytics/sales?days=60")
    assert response.status_code == 200
    assert response.json() == {"data": "sales analytics data"}
    mock_get_sales.assert_called_once_with(days=60)


@patch("src.services.analytics_service.AnalyticsService.get_customer_analytics", new_callable=AsyncMock)
async def test_get_customer_analytics_success(mock_get_customers):
    mock_get_customers.return_value = {"data": "customer analytics data"}
    response = client.get("/api/v1/analytics/customers?days=90")
    assert response.status_code == 200
    assert response.json() == {"data": "customer analytics data"}
    mock_get_customers.assert_called_once_with(days=90)


@patch("src.services.analytics_service.AnalyticsService.get_product_analytics", new_callable=AsyncMock)
async def test_get_product_analytics_success(mock_get_products):
    mock_get_products.return_value = {"data": "product analytics data"}
    response = client.get("/api/v1/analytics/products?days=30")
    assert response.status_code == 200
    assert response.json() == {"data": "product analytics data"}
    mock_get_products.assert_called_once_with(days=30)


@patch("src.services.analytics_service.AnalyticsService.get_crm_analytics", new_callable=AsyncMock)
async def test_get_crm_analytics_success(mock_get_crm):
    mock_get_crm.return_value = {"data": "crm analytics data"}
    response = client.get("/api/v1/analytics/crm?days=30")
    assert response.status_code == 200
    assert response.json() == {"data": "crm analytics data"}
    mock_get_crm.assert_called_once_with(days=30)

# Example of a test for authentication/authorization (simplified)
@patch("src.services.analytics_service.AnalyticsService.get_comprehensive_dashboard", new_callable=AsyncMock)
async def test_get_comprehensive_dashboard_unauthorized(mock_get_dashboard):
    # Temporarily override get_current_active_user to simulate unauthenticated/unauthorized user
    original_override = app.dependency_overrides.get(get_current_active_user)

    async def mock_get_unauthorized_user():
        # Simulate a user without the 'analyst' role or necessary permissions
        return {**MOCK_USER, "roles": ["guest"]}

    app.dependency_overrides[get_current_active_user] = mock_get_unauthorized_user

    response = client.get("/api/v1/analytics/dashboard?days=30")

    # Based on typical FastAPI patterns, 403 is common for permission issues when user is authenticated but lacks specific permission.
    assert response.status_code == 403, response.text

    # Restore original override
    if original_override is not None: # Check if it was actually set
        app.dependency_overrides[get_current_active_user] = original_override
    elif get_current_active_user in app.dependency_overrides: # Check before deleting
        del app.dependency_overrides[get_current_active_user]

    mock_get_dashboard.assert_not_called() # Ensure service method wasn't called
